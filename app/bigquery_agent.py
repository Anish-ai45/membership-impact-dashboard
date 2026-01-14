"""
BigQuery Agent - Queries facts from BigQuery tables
"""
from google.cloud import bigquery
import os
from typing import Dict, List, Optional, Any

class BigQueryAgent:
    """Agent that queries membership and provider data from BigQuery"""
    
    def __init__(self, project_id: str, dataset: str = "membership_analytics"):
        self.project_id = project_id
        self.dataset = dataset
        self.client = bigquery.Client(project=project_id)
    
    def get_membership_data(self, org_cd: str) -> Optional[Dict[str, Any]]:
        """Query membership data for a specific organization"""
        query = f"""
        SELECT *
        FROM `{self.project_id}.{self.dataset}.membership_impact`
        WHERE org_cd = @org_cd
        LIMIT 1
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("org_cd", "STRING", org_cd)
            ]
        )
        
        try:
            query_job = self.client.query(query, job_config=job_config)
            results = query_job.result()
            
            for row in results:
                # Convert row to dict
                return dict(row)
            return None
        except Exception as e:
            print(f"BigQuery error: {e}")
            return None
    
    def get_provider_changes(self, org_cd: str) -> List[Dict[str, Any]]:
        """Query provider configuration changes for a specific organization"""
        query = f"""
        SELECT *
        FROM `{self.project_id}.{self.dataset}.provider_config_changes`
        WHERE org_cd = @org_cd
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("org_cd", "STRING", org_cd)
            ]
        )
        
        try:
            query_job = self.client.query(query, job_config=job_config)
            results = query_job.result()
            
            return [dict(row) for row in results]
        except Exception as e:
            print(f"BigQuery error: {e}")
            return []
    
    def query_custom(self, sql_query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a custom SQL query"""
        job_config = bigquery.QueryJobConfig()
        
        if parameters:
            query_params = [
                bigquery.ScalarQueryParameter(key, "STRING", value)
                for key, value in parameters.items()
            ]
            job_config.query_parameters = query_params
        
        try:
            query_job = self.client.query(sql_query, job_config=job_config)
            results = query_job.result()
            return [dict(row) for row in results]
        except Exception as e:
            print(f"BigQuery error: {e}")
            return []
