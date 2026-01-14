"""
Orchestrator Agent - Coordinates BigQuery Agent and PDF RAG Agent, then generates LLM response
"""
from typing import Dict, Any, Optional, List
from bigquery_agent import BigQueryAgent
from pdf_rag_agent import PDFRAGAgent
from prompts import SYSTEM_PROMPT, build_response_prompt
import vertexai
from vertexai.generative_models import GenerativeModel
import re

class OrchestratorAgent:
    """Orchestrates multiple agents and generates final response"""
    
    def __init__(self, config):
        self.config = config
        # Initialize Vertex AI before creating models
        vertexai.init(project=config.project_id, location=config.region)
        self.bq_agent = BigQueryAgent(config.project_id, dataset="membership_analytics")
        self.rag_agent = PDFRAGAgent(config)
        self.llm = GenerativeModel(config.chat_model)
    
    def extract_org_cd(self, query: str) -> Optional[str]:
        """Extract organization code from query"""
        # Try new format first (SXXXX_PXXX)
        match = re.search(r'([A-Z]\d{4}_P\d{3})', query)
        if match:
            return match.group(1)
        
        # Fall back to old format
        match = re.search(r'(?:org|ORG)[_\s]*(\d+)', query, re.IGNORECASE)
        if match:
            org_num = match.group(1).zfill(3)
            return f"ORG_{org_num}"
        
        return None
    
    def compute_signals(self, membership_data: Dict, provider_changes: List[Dict]) -> Dict[str, Any]:
        """Compute analytical signals from membership and provider data"""
        signals = {}
        
        if not membership_data:
            return signals
        
        # Extract values - handle string numbers from BigQuery
        def safe_int(value, default=0):
            if value is None:
                return default
            try:
                return int(float(str(value)))
            except:
                return default
        
        def safe_float(value, default=0.0):
            if value is None:
                return default
            try:
                return float(str(value))
            except:
                return default
        
        dropped_mbr_cnt = safe_int(membership_data.get('dropped_mbr_cnt_x202512m12_prd_vs_x202511m11_prd', 0))
        dropped_per = safe_float(membership_data.get('dropped_per', 0))
        new_mbr_cnt = safe_int(membership_data.get('new_mbr_cnt_x202512m12_prd_vs_x202511m11_prd', 0))
        new_per = safe_float(membership_data.get('new_members_percentage', 0))
        net_change = safe_int(membership_data.get('com_mbr_cnt_x202512m12_prd_vs_x202511m11_prd', 0))
        
        movement = (membership_data.get('moved_from_org_cd') is not None and 
                   str(membership_data.get('moved_from_org_cd')).lower() != 'null') or \
                  (membership_data.get('moved_to_org_cd') is not None and 
                   str(membership_data.get('moved_to_org_cd')).lower() != 'null')
        
        retro_term_mem_count = safe_int(membership_data.get('retro_term_mem_count', 0))
        
        # Compute signals
        signals['dropped_mbr_cnt'] = dropped_mbr_cnt
        signals['dropped_per'] = dropped_per
        signals['new_mbr_cnt'] = new_mbr_cnt
        signals['new_per'] = new_per
        signals['net_change'] = net_change
        signals['movement'] = movement
        signals['retro_dominant'] = retro_term_mem_count >= 0.30 * dropped_mbr_cnt if dropped_mbr_cnt > 0 else False
        signals['drop_high'] = dropped_per > 10 or dropped_mbr_cnt > 50000
        
        # Churn
        dropped_high = dropped_mbr_cnt > 50000 or dropped_per > 10
        new_high = new_mbr_cnt > 30000 or new_per > 8
        net_small = abs(net_change) < 0.25 * dropped_mbr_cnt if dropped_mbr_cnt > 0 else False
        signals['churn'] = dropped_high and new_high and net_small
        
        # Provider signals
        has_termed_key = any(
            str(change.get('key_type', '')).lower() == 'termed key' 
            for change in provider_changes
        )
        has_file_id = any(
            'file_id' in str(change.get('keys_changed', '')).lower() or 
            'file_id' in str(change.get('test_type', '')).lower()
            for change in provider_changes
        )
        has_plan_carrier_id = any(
            'plan_carrier_id' in str(change.get('keys_changed', '')).lower() or 
            'plan_carrier_id' in str(change.get('test_type', '')).lower()
            for change in provider_changes
        )
        has_network_id = any(
            'network_id' in str(change.get('keys_changed', '')).lower() or 
            'network_id' in str(change.get('test_type', '')).lower()
            for change in provider_changes
        )
        
        signals['has_termed_key'] = has_termed_key
        signals['has_file_id'] = has_file_id
        signals['has_plan_carrier_id'] = has_plan_carrier_id
        signals['has_network_id'] = has_network_id
        signals['change_count'] = len(provider_changes)
        
        return signals
    
    def run(self, query: str) -> Dict[str, Any]:
        """Main orchestration method"""
        # Step 1: Extract org_cd from query
        org_cd = self.extract_org_cd(query)
        if not org_cd:
            return {
                'text': "Please specify an organization code like S5660_P801 or ORG_003.",
                'data': {},
                'signals': {},
                'org_cd': None
            }
        
        # Step 2: BigQuery Agent - Get facts
        membership_data = self.bq_agent.get_membership_data(org_cd)
        if not membership_data:
            return {
                'text': f"No data found for {org_cd} in BigQuery. Please check the organization code.",
                'data': {},
                'signals': {},
                'org_cd': org_cd
            }
        
        provider_changes = self.bq_agent.get_provider_changes(org_cd)
        signals = self.compute_signals(membership_data, provider_changes)
        
        # Step 3: PDF RAG Agent - Get context from rulebook
        # Build RAG query based on signals
        rag_query = "membership drop explanation rules provider configuration changes retro termination movement churn"
        if signals.get('retro_dominant'):
            rag_query += " retro_term_mem_count retroactive terminations"
        if signals.get('has_termed_key'):
            rag_query += " termed key"
        if signals.get('has_file_id'):
            rag_query += " file_id mapping"
        if signals.get('has_plan_carrier_id'):
            rag_query += " plan_carrier_id carrier mapping"
        if signals.get('has_network_id'):
            rag_query += " network_id network mapping"
        
        rules_chunks = self.rag_agent.retrieve(rag_query, top_k=4)
        rules_text = "\n\n---\n\n".join(rules_chunks) if rules_chunks else ""
        
        # Step 4: Prepare data for LLM
        def safe_int(value, default=0):
            if value is None:
                return default
            try:
                return int(float(str(value)))
            except:
                return default
        
        prior = safe_int(membership_data.get('mbr_cnt_x202511m11_prd', 0))
        current = safe_int(membership_data.get('mbr_cnt_x202512m12_prd', 0))
        
        membership_for_prompt = {
            'org_cd': org_cd,
            'prior_members': prior,
            'current_members': current,
            'dropped_mbr_cnt': signals['dropped_mbr_cnt'],
            'dropped_per': signals['dropped_per'],
            'new_mbr_cnt': signals['new_mbr_cnt'],
            'new_per': signals['new_per'],
            'net_change': signals['net_change'],
            'movement': signals['movement'],
            'retro_term_mem_count': safe_int(membership_data.get('retro_term_mem_count', 0))
        }
        
        # Step 5: Generate LLM response
        prompt = build_response_prompt(
            membership_for_prompt,
            signals,
            rules_text,
            len(provider_changes),
            query
        )
        
        try:
            response = self.llm.generate_content(
                SYSTEM_PROMPT + "\n\n" + prompt
            )
            generated_text = response.text.strip()
            
            return {
                'text': generated_text,
                'data': membership_for_prompt,
                'signals': signals,
                'org_cd': org_cd,
                'source': 'bigquery'  # Indicate data source
            }
        except Exception as e:
            # Enhanced fallback response with reasoning
            prior = membership_for_prompt['prior_members']
            current = membership_for_prompt['current_members']
            dropped_cnt = signals.get('dropped_mbr_cnt', 0)
            dropped_per = signals.get('dropped_per', 0)
            new_cnt = signals.get('new_mbr_cnt', 0)
            new_per = signals.get('new_per', 0)
            net_change = signals['net_change']
            has_increase = net_change > 0
            
            # Build analytical fallback with reasoning
            fallback_text = f"Analysis for {org_cd}:\n\n"
            
            # State the facts
            if "drop" in query.lower() and has_increase:
                fallback_text += f"Actually, membership didn't drop - it increased by {net_change:,} members ({new_per:.2f}% growth). "
                fallback_text += f"The organization grew from {prior:,} to {current:,} members. "
            elif net_change < 0:
                fallback_text += f"Membership decreased by {abs(net_change):,} members ({dropped_per:.2f}% drop), from {prior:,} to {current:,} members. "
            else:
                change_pct = ((net_change/prior)*100) if prior > 0 else 0
                fallback_text += f"Membership changed by {net_change:+,} members ({change_pct:+.2f}% change), from {prior:,} to {current:,} members. "
            
            # Explain the patterns
            if dropped_cnt > 0 or new_cnt > 0:
                fallback_text += f"\n\nLooking at member movement: {dropped_cnt:,} members dropped ({dropped_per:.2f}% of prior period) while {new_cnt:,} new members were added ({new_per:.2f}% of prior period). "
                if dropped_cnt > 0 and new_cnt == 0:
                    fallback_text += "The net decrease is entirely due to dropped members with no new additions. "
                elif new_cnt > dropped_cnt:
                    fallback_text += f"The net increase suggests that new member additions ({new_cnt:,}) outweighed the drops ({dropped_cnt:,}). "
                elif dropped_cnt > new_cnt:
                    fallback_text += f"The net decrease indicates that member drops ({dropped_cnt:,}) exceeded new additions ({new_cnt:,}). "
            
            # Reason about causes based on signals
            causes = []
            if signals.get('movement'):
                causes.append("membership movement between organizations (suggesting re-attribution or reassignment of members)")
            if signals.get('retro_dominant') and dropped_cnt > 0:
                retro_term = membership_for_prompt.get('retro_term_mem_count', 0)
                retro_pct = (retro_term / dropped_cnt * 100) if dropped_cnt > 0 else 0
                causes.append(f"retroactive terminations ({retro_term:,} members, {retro_pct:.1f}% of drops, suggesting data corrections or backdated terminations)")
            config_changes = []
            if signals.get('has_network_id'):
                config_changes.append("network ID mapping")
            if signals.get('has_plan_carrier_id'):
                config_changes.append("plan carrier ID mapping")
            if signals.get('has_file_id'):
                config_changes.append("file ID mapping")
            if config_changes:
                causes.append(f"provider configuration changes ({', '.join(config_changes)} changes that can re-attribute membership)")
            
            if causes:
                fallback_text += f"\n\nThe data shows several indicators that help explain this change: {', '.join(causes)}. "
                fallback_text += "These signals suggest that the membership change may be related to data reclassification, member reassignment, or configuration updates rather than actual membership loss or gain."
            
            # Provide insights
            if signals.get('churn'):
                fallback_text += "\n\nThis pattern of high drops offset by high additions (churn pattern) typically indicates member reclassification or movement between organizations rather than actual membership loss."
            
            return {
                'text': fallback_text,
                'data': membership_for_prompt,
                'signals': signals,
                'org_cd': org_cd,
                'source': 'bigquery'
            }
