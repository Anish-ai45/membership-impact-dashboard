"""
ADK Orchestrator Agent - ADK-based agent that coordinates tools and generates responses
"""
from typing import Dict, Any, Optional, List
from google.adk import Agent, Runner
from google.adk.tools import FunctionTool
from google.adk.models.google_llm import Gemini
from google.adk.sessions import InMemorySessionService
from google.genai import types
from adk_tools import create_bigquery_tools, create_rag_tools
from prompts import SYSTEM_PROMPT, build_response_prompt
from orchestrator_agent import OrchestratorAgent  # For compute_signals and extract_org_cd
from dotenv import load_dotenv  # Ensure .env is loaded before config
import re
import uuid

# Load .env file early to ensure environment variables are available
load_dotenv()

# Set API key as environment variable for Google AI API
# ADK/Gemini reads from GOOGLE_API_KEY environment variable
import os
if not os.getenv('GOOGLE_API_KEY'):
    # Set default API key if not in environment
    os.environ['GOOGLE_API_KEY'] = 'AIzaSyAPNH7XSAM4RXMvISmTQZl26s1jk90yFDM'


class ADKOrchestratorAgent:
    """ADK-based orchestrator agent that coordinates tools and generates responses"""
    
    def __init__(self, config):
        self.config = config
        
        # Verify API key is loaded (required for Google AI API)
        if not config.api_key:
            raise ValueError(
                "GOOGLE_AI_API_KEY is not set. "
                "Please ensure .env file is loaded and contains GOOGLE_AI_API_KEY."
            )
        
        # Create tools
        # Note: BigQuery still needs project_id, but it's optional for API key mode
        project_id = config.project_id or "default-project"  # Fallback for BigQuery
        bq_tools = create_bigquery_tools(project_id, dataset="membership_analytics")
        rag_tools = create_rag_tools(config)
        all_tools = bq_tools + rag_tools
        
        # Create Gemini model with Google AI API key (not Vertex AI)
        # ADK/Gemini reads API key from GOOGLE_API_KEY environment variable
        # Ensure it's set before creating the model
        if config.api_key and not os.getenv('GOOGLE_API_KEY'):
            os.environ['GOOGLE_API_KEY'] = config.api_key
        
        # Create Gemini model - it will read API key from environment
        gemini_model = Gemini(
            model=config.chat_model
            # API key is read from GOOGLE_API_KEY environment variable
        )
        
        # Create ADK agent with tools and configured Gemini model
        # ADK Agent requires: name, model, tools
        self.agent = Agent(
            name="membership_analyst",
            description="Analyzes membership changes using BigQuery data and PDF rulebook context",
            model=gemini_model,  # Use configured Gemini model instance
            tools=all_tools,
            instruction=SYSTEM_PROMPT  # Use system prompt as agent instruction
        )
        
        # Create session service and runner
        # Runner requires app_name along with agent
        self.app_name = "membership_analyst_app"
        self.session_service = InMemorySessionService()
        self.runner = Runner(
            app_name=self.app_name,
            agent=self.agent,
            session_service=self.session_service
        )
        
        # Keep reference to original orchestrator for helper methods
        self._temp_orchestrator = OrchestratorAgent(config)
        
        # Session management - use persistent session for chat continuity
        self.user_id = "dashboard_user"
        # Create a single session ID that persists for the agent instance
        # This allows ADK to maintain chat continuity across requests
        self.session_id = str(uuid.uuid4())
        
        # Create session in session service immediately
        # This ensures the session exists before any Runner.run() calls
        try:
            # Check if session exists, create if not
            existing_session = self.session_service.get_session_sync(
                app_name=self.app_name,
                user_id=self.user_id,
                session_id=self.session_id
            )
            if existing_session is None:
                self.session_service.create_session_sync(
                    app_name=self.app_name,
                    user_id=self.user_id,
                    session_id=self.session_id
                )
        except Exception as e:
            # If get fails, try create directly
            try:
                self.session_service.create_session_sync(
                    app_name=self.app_name,
                    user_id=self.user_id,
                    session_id=self.session_id
                )
            except Exception as create_error:
                print(f"Warning: Could not create initial session: {create_error}")
                # Session will be created on first use if needed
    
    def extract_org_cd(self, query: str) -> Optional[str]:
        """Extract organization code from query"""
        return self._temp_orchestrator.extract_org_cd(query)
    
    def compute_signals(self, membership_data: Dict, provider_changes: List[Dict]) -> Dict[str, Any]:
        """Compute analytical signals from membership and provider data"""
        return self._temp_orchestrator.compute_signals(membership_data, provider_changes)
    
    def run(self, query: str) -> Dict[str, Any]:
        """Main orchestration method using ADK agent"""
        # Step 1: Extract org_cd from query
        org_cd = self.extract_org_cd(query)
        if not org_cd:
            return {
                'text': "Please specify an organization code like S5660_P801 or ORG_003.",
                'data': {},
                'signals': {},
                'org_cd': None
            }
        
        # Step 2: Get data first (needed for signals and UI)
        bq_agent = self._temp_orchestrator.bq_agent
        membership_data = bq_agent.get_membership_data(org_cd)
        provider_changes = bq_agent.get_provider_changes(org_cd)
        
        if not membership_data:
            return {
                'text': f"No data found for {org_cd} in BigQuery. Please check the organization code.",
                'data': {},
                'signals': {},
                'org_cd': org_cd
            }
        
        signals = self.compute_signals(membership_data, provider_changes)
        
        # Step 3: Build RAG query based on signals
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
        
        # Step 4: Prepare data for prompt
        def safe_int(value, default=0):
            if value is None:
                return default
            try:
                return int(float(str(value)))
            except:
                return default
        
        prior = safe_int(membership_data.get('mbr_cnt_x202511m11_prd', 0))
        current = safe_int(membership_data.get('mbr_cnt_x202512m12_prd', 0))
        
        # Step 5: Get RAG context (ADK agent can use tool, but we'll provide it for consistency)
        rules_chunks = self._temp_orchestrator.rag_agent.retrieve(rag_query, top_k=4)
        rules_text = "\n\n---\n\n".join(rules_chunks) if rules_chunks else ""
        
        # Step 6: Build enriched query with context for ADK agent
        # ADK agent has tools available, but we provide structured context
        enriched_query = build_response_prompt(
            {
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
            },
            signals,
            rules_text,  # Include RAG context
            len(provider_changes),
            query
        )
        
        # Step 7: Use ADK Runner to execute agent
        try:
            # Use persistent session ID for chat continuity
            # Session was created in __init__, but verify it exists
            try:
                session = self.session_service.get_session_sync(
                    app_name=self.app_name,
                    user_id=self.user_id,
                    session_id=self.session_id
                )
                # If session doesn't exist (shouldn't happen, but handle it), create it
                if session is None:
                    self.session_service.create_session_sync(
                        app_name=self.app_name,
                        user_id=self.user_id,
                        session_id=self.session_id
                    )
            except Exception as session_error:
                # If get fails, try create directly
                try:
                    self.session_service.create_session_sync(
                        app_name=self.app_name,
                        user_id=self.user_id,
                        session_id=self.session_id
                    )
                except Exception as create_error:
                    print(f"Session setup warning: {create_error}")
            
            # Create message for ADK
            message = types.Content(parts=[types.Part(text=enriched_query)])
            
            # Run ADK agent via Runner
            # Use persistent session_id for chat continuity
            # Runner.run() returns a generator with async operations
            # We need to handle this carefully to avoid event loop issues
            events = self.runner.run(
                user_id=self.user_id,
                session_id=self.session_id,  # Reuse same session for continuity
                new_message=message
            )
            
            # Process events to get final response
            # Collect all events first to ensure generator is fully consumed
            generated_text = ""
            events_list = []
            
            try:
                # Fully consume the generator to complete async operations
                # This must complete before any cleanup happens
                for event in events:
                    events_list.append(event)
                    
            except RuntimeError as runtime_error:
                # RuntimeError('Event loop is closed') happens during async cleanup
                # This occurs AFTER events are processed, so it's non-critical
                if "Event loop is closed" in str(runtime_error):
                    # Events were already collected, cleanup error is safe to ignore
                    if events_list:
                        # Silently continue - we have events, cleanup error is harmless
                        pass
                    else:
                        # No events - this is a real problem
                        print(f"Error: Event loop closed before events received: {runtime_error}")
                        return self._temp_orchestrator.run(query)
                else:
                    # Other RuntimeError - re-raise or handle
                    if not events_list:
                        return self._temp_orchestrator.run(query)
                    # If we have events, continue processing
            except Exception as event_error:
                # Other errors during event consumption
                if not events_list:
                    # No events collected - fallback
                    print(f"Error consuming events: {event_error}")
                    return self._temp_orchestrator.run(query)
                else:
                    # Got some events, log but continue
                    print(f"Warning during event processing: {event_error}")
            
            # Process collected events
            for event in events_list:
                # Look for content events
                if hasattr(event, 'content'):
                    if isinstance(event.content, str):
                        generated_text += event.content
                    elif hasattr(event.content, 'text'):
                        generated_text += event.content.text
                elif hasattr(event, 'text'):
                    generated_text += event.text
                elif hasattr(event, 'parts'):
                    for part in event.parts:
                        if hasattr(part, 'text'):
                            generated_text += part.text
            
            # If no text extracted, use fallback
            if not generated_text.strip():
                # Fallback: use original orchestrator for LLM generation
                return self._temp_orchestrator.run(query)
            
            # Prepare data for UI
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
            
            return {
                'text': generated_text.strip(),
                'data': membership_for_prompt,
                'signals': signals,
                'org_cd': org_cd,
                'source': 'adk'
            }
            
        except Exception as e:
            print(f"ADK agent error: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to original orchestrator
            return self._temp_orchestrator.run(query)
