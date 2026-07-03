import logging
import os
import json
import warnings
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

# Optional imports for AI providers
try:
    import openai
except ImportError:
    openai = None

try:
    from google import genai
except ImportError:
    genai = None

try:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=FutureWarning)
        import google.generativeai as genai_legacy
except ImportError:
    genai_legacy = None

try:
    import anthropic
except ImportError:
    anthropic = None

class HotelAIEngine(models.AbstractModel):
    """
    Bridge between Odoo and LLM Providers (OpenAI, Anthropic, Gemini).
    """
    _name = 'hotel.ai.engine'
    _description = 'Hotel AI Engine'

    def _get_api_key(self, provider):
        """Retrieve API key from Odoo Config or Env."""
        # Config Params > Env > Hardcoded (avoid hardcoded)
        params = self.env['ir.config_parameter'].sudo()
        if provider == 'openai':
            return params.get_param('hotel.ai.openai_key') or os.getenv('OPENAI_API_KEYS')
        elif provider == 'gemini':
            return params.get_param('hotel.ai.gemini_key') or os.getenv('GEMINI_API_KEYS')
        elif provider == 'claude':
            return params.get_param('hotel.ai.claude_key') or os.getenv('CLAUDE_API_KEYS')
        return None

    @api.model
    def query_bot(self, prompt, context_data=None, provider=None):
        """
        Main entry point to query the AI.
        :param prompt: User's question or system instruction
        :param context_data: Dict of data to include (metrics, logs)
        :param provider: Force a provider (optional, defaults to primary brain)
        :return: String response or JSON dict
        """
        params = self.env['ir.config_parameter'].sudo()
        primary = provider or params.get_param('hotel.ai.primary_brain', 'openai')
        enable_failover = params.get_param('hotel.ai.enable_failover', True)

        # 1. Build context-rich prompt
        full_prompt = f"Context Data:\n{json.dumps(context_data, default=str)}\n\nQuery: {prompt}\n\nProvide a professional, executive-level response."
        
        # 2. Try Primary Provider
        try:
            response = self._try_provider(primary, full_prompt)
            if response:
                return response
        except Exception as e:
            _logger.error(f"Primary AI Brain ({primary}) failed: {e}")
            
        # 3. Failover (if enabled)
        if enable_failover:
            for p in ['openai', 'gemini', 'claude']:
                if p != primary:
                    try:
                        response = self._try_provider(p, full_prompt)
                        if response:
                            _logger.info(f"Failover successful to {p}")
                            return response
                    except Exception:
                        continue
        
        return _("I'm sorry, all AI brains are currently unreachable or experiencing issues. Please check your API keys in Settings.")

    def _try_provider(self, provider, prompt):
        key = self._get_api_key(provider)
        if not key:
            raise ValueError(_("No API key found for %s in Settings.") % provider.capitalize())

        # Handle multiple keys in env (comma-separated)
        key = key.split(',')[0].strip()

        if provider == 'openai':
            if not openai:
                raise ImportError(_("The 'openai' Python library is not installed."))
            client = openai.OpenAI(api_key=key)
            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}]
            )
            return resp.choices[0].message.content

        elif provider == 'gemini':
            if genai:
                # Modern Client-based implementation (google-genai v1+)
                client = genai.Client(api_key=key)
                models_to_try = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-flash-latest"]
                last_error = None
                for m_name in models_to_try:
                    try:
                        resp = client.models.generate_content(
                            model=m_name,
                            contents=prompt
                        )
                        if resp and resp.text:
                            return resp.text
                    except Exception as e:
                        last_error = e
                        continue
                raise ValueError(_("Gemini failed after trying multiple models. Last error: %s") % last_error)

            elif genai_legacy:
                # Legacy implementation (google-generativeai)
                genai_legacy.configure(api_key=key)
                models_to_try = ["gemini-1.5-flash", "gemini-pro", "gemini-1.5-pro"]
                last_error = None
                for m_name in models_to_try:
                    try:
                        model = genai_legacy.GenerativeModel(m_name)
                        resp = model.generate_content(prompt)
                        if resp and resp.text:
                            return resp.text
                    except Exception as e:
                        last_error = e
                        continue
                raise ValueError(_("Gemini (Legacy) failed after trying multiple models. Last error: %s") % last_error)
            else:
                raise ImportError(_("The 'google-genai' or 'google-generativeai' Python library is not installed."))

        elif provider == 'claude':
            if not anthropic:
                raise ImportError(_("The 'anthropic' Python library is not installed."))
            client = anthropic.Anthropic(api_key=key)
            message = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text
        
        return None

    @api.model
    def analyze_dashboard(self, dashboard_data):
        """Generates a summary of the current dashboard state."""
        prompt = """
        Analyze this hotel dashboard data. 
        Identify 3 key wins and 3 critical risks. 
        Suggestion 1 concrete action for the General Manager.
        Format as HTML with <b>bold</b> highlights.
        """
        return self.query_bot(prompt, dashboard_data, provider='openai')

    @api.model
    def get_pricing_suggestion(self, occupancy_data):
        """Specific method for the Dynamic Pricing Smart Box."""
        prompt = """
        Based on the occupancy trends, suggest a pricing strategy for the next 7 days.
        Return strictly JSON: {"suggestion": "text", "action": "text", "impact": "text"}
        """
        # Force JSON response logic if needed, or parse the text
        response = self.query_bot(prompt, occupancy_data, provider='openai')
        try:
            # Simple cleanup for JSON parsing
            clean_json = response.replace('```json', '').replace('```', '')
            return json.loads(clean_json)
        except:
            return {
                "suggestion": "Keep rates steady.",
                "action": "Monitor closely.",
                "impact": "Stable revenue."
            }
