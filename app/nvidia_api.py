# NVIDIA API client for resume analysis
import os
import requests
from typing import Dict, Any

from app.config import NVIDIA_API_KEY, NVIDIA_MODEL_ID


class NVIDIAClient:
    def __init__(self):
        self.api_key = os.getenv("NVIDIA_API_KEY")
        self.model_id = os.getenv("NVIDIA_MODEL_ID", "nvidia/nemotron-4-340b")
        if not self.api_key:
            raise ValueError("NVIDIA_API_KEY is required for NVIDIA API client")

    def analyze_resume(self, resume_text: str) -> Dict[str, Any]:
        """
        Send resume text to NVIDIA inference API and return parsed analysis.
        Returns a dictionary with analysis results or error information.
        """
        api_url = f"https://api.nvidia.com/v1/models/{self.model_id}/infer"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "inputs": resume_text,
            "parameters": {
                "max_tokens": 1024,
                "temperature": 0.3,
                "top_p": 0.9
            }
        }

        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            analysis = {
                "model_used": self.model_id,
                "status": "success",
                "processing_time": "success",
                "analysis": result.get("output", {})
            }
            return analysis
        except requests.exceptions.RequestException as e:
            return {
                "error": "NVIDIA request failed: " + str(e),
                "status": "api_error"
            }
        except Exception as e:
            return {
                "error": "Unexpected error during analysis: " + str(e),
                "status": "error"
            }