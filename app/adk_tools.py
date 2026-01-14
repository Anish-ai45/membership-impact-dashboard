"""
ADK Tools - Convert BigQuery and PDF RAG agents to ADK FunctionTool
"""
from typing import Dict, Any, List, Optional
from google.adk.tools import FunctionTool
from google.cloud import bigquery
import os
import re
import faiss
import numpy as np
from vertexai.language_models import TextEmbeddingModel

# Import existing agents for their functionality
from bigquery_agent import BigQueryAgent
from pdf_rag_agent import PDFRAGAgent


def create_bigquery_tools(project_id: str, dataset: str = "membership_analytics") -> List[FunctionTool]:
    """Create ADK FunctionTools for BigQuery operations"""
    
    bq_agent = BigQueryAgent(project_id, dataset)
    
    def get_membership_data(org_cd: str) -> Dict[str, Any]:
        """Query membership data for a specific organization code from BigQuery.
        
        This tool queries the membership_impact table to get membership metrics
        including prior period, current period, dropped members, new members,
        and retroactive terminations.
        
        Args:
            org_cd: Organization code (e.g., S5660_P801 or ORG_003)
            
        Returns:
            Dictionary with membership data including:
            - mbr_cnt_x202511m11_prd: Prior period member count
            - mbr_cnt_x202512m12_prd: Current period member count
            - dropped_mbr_cnt_x202512m12_prd_vs_x202511m11_prd: Dropped members
            - new_mbr_cnt_x202512m12_prd_vs_x202511m11_prd: New members
            - retro_term_mem_count: Retroactive terminations
            Returns empty dict if not found
        """
        result = bq_agent.get_membership_data(org_cd)
        return result if result else {}
    
    def get_provider_changes(org_cd: str) -> List[Dict[str, Any]]:
        """Query provider configuration changes for a specific organization code from BigQuery.
        
        This tool queries the provider_config_changes table to get configuration
        changes that may affect membership attribution, such as network ID mapping,
        plan carrier ID mapping, file ID mapping, or termed key changes.
        
        Args:
            org_cd: Organization code (e.g., S5660_P801 or ORG_003)
            
        Returns:
            List of dictionaries with provider configuration changes including:
            - key_type: Type of configuration key changed
            - keys_changed: Details of what changed
            - test_type: Type of change/test
            Returns empty list if no changes found
        """
        return bq_agent.get_provider_changes(org_cd)
    
    # Create FunctionTools
    # FunctionTool uses function docstring and name automatically
    membership_tool = FunctionTool(func=get_membership_data)
    provider_tool = FunctionTool(func=get_provider_changes)
    
    return [membership_tool, provider_tool]


def create_rag_tools(config) -> List[FunctionTool]:
    """Create ADK FunctionTool for PDF RAG operations"""
    
    rag_agent = PDFRAGAgent(config)
    
    def retrieve_rulebook_context(query: str, top_k: int = 4) -> str:
        """Retrieve relevant context from the membership impact rulebook PDF using semantic search.
        
        This tool searches the PDF rulebook for relevant sections that explain
        membership impact patterns, rules, and analysis frameworks. Use this when
        you need to reference specific rules or patterns from the rulebook.
        
        Args:
            query: Search query describing what rulebook content you need
                   (e.g., "retroactive terminations", "network ID mapping changes",
                   "membership drop explanation rules")
            top_k: Number of top relevant chunks to retrieve (default: 4)
            
        Returns:
            Combined text of relevant rulebook chunks separated by "---"
            Returns empty string if no relevant content found
        """
        chunks = rag_agent.retrieve(query, top_k=top_k)
        return "\n\n---\n\n".join(chunks) if chunks else ""
    
    # Create FunctionTool
    # FunctionTool uses function docstring and name automatically
    rag_tool = FunctionTool(func=retrieve_rulebook_context)
    
    return [rag_tool]
