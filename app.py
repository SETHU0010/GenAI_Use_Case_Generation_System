import streamlit as st
import requests
from bs4 import BeautifulSoup
from googlesearch import search
import google.generativeai as genai
from playwright.sync_api import sync_playwright

# --- SET YOUR GEMINI API KEY DIRECTLY HERE ---
GEMINI_API_KEY = "AIzaSyBChIHuCoikBLObEQlzIw4MXbtxEuf3Nkk"  # <-- replace with your own!

# Configure Gemini
try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-pro')
except Exception as e:
    st.warning(f"Gemini configuration failed: {e}")
    model = None

# --- Agent Classes ---

class ResearchAgent:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }

    def research_company(self, company_name):
        info = self.browse_website(company_name)
        if not info['offerings'] or not info['focus_areas']:
            info = self.fallback_company_info(company_name)
        return info

    def research_industry(self, industry):
        return self.browse_industry(industry)

    def browse_website(self, company_name):
        try:
            results = list(search(company_name, num_results=2, lang="en"))
            if not results:
                st.warning("No website found from search. Falling back.")
                return {"offerings": [], "focus_areas": [], "url": None}

            url = results[0]
            if not url.startswith("http"):
                url = "https://" + url

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, timeout=60000)
                page_content = page.content()
                browser.close()

            soup = BeautifulSoup(page_content, "html.parser")

            offerings = [
                el.text for el in soup.find_all(["li", "p", "span"])
                if any(word in el.text.lower() for word in ["product", "solution", "service", "offering"])
            ]
            focus_areas = [
                el.text for el in soup.find_all(["p", "div"])
                if any(word in el.text.lower() for word in ["mission", "vision", "focus", "strategy"])
            ]

            return {
                "offerings": offerings[:5],
                "focus_areas": focus_areas[:5],
                "url": url,
            }
        except Exception as e:
            st.error(f"Error browsing website: {str(e)}")
            return {"offerings": [], "focus_areas": [], "url": None}

    def fallback_company_info(self, company_name):
        if model is None:
            st.warning("Gemini fallback unavailable. No company info.")
            return {"offerings": ["General product offerings"], "focus_areas": ["General business focus"], "url": f"https://www.google.com/search?q={company_name}"}

        prompt = f"Provide a brief about {company_name}: key product offerings and strategic focus areas."
        try:
            response = model.generate_content(prompt)
            if hasattr(response, 'text'):
                text = response.text
                return {
                    "offerings": [text.split('\n')[0] if '\n' in text else text],
                    "focus_areas": [text.split('\n')[1] if '\n' in text else "General focus area"],
                    "url": f"https://www.google.com/search?q={company_name}"
                }
            else:
                return {"offerings": [], "focus_areas": [], "url": None}
        except Exception as e:
            st.error(f"Gemini fallback failed: {e}")
            return {"offerings": [], "focus_areas": [], "url": None}

    def browse_industry(self, industry):
        try:
            results = list(search(industry + " industry overview", num_results=2, lang="en"))
            if not results:
                st.warning("No industry overview found.")
                return {"trends": [], "standards": [], "url": None}
            url = results[0]
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            trends = [
                el.text for el in soup.find_all("li")
                if "trend" in el.text.lower() or "challenge" in el.text.lower()
            ]
            standards = [
                el.text for el in soup.find_all("p")
                if "standard" in el.text.lower() or "regulation" in el.text.lower()
            ]

            return {
                "trends": trends[:5] if trends else ["General industry trends"],
                "standards": standards[:5] if standards else ["General industry standards"],
                "url": url,
            }
        except Exception as e:
            st.error(f"Error browsing industry website: {e}")
            return {"trends": [], "standards": [], "url": None}

class UseCaseAgent:
    def __init__(self):
        self.use_cases = []

    def generate_use_cases(self, company_info, industry_info):
        focus_areas = company_info.get('focus_areas', [])
        offerings = company_info.get('offerings', [])
        trends = industry_info.get('trends', [])

        focus_area = focus_areas[0] if focus_areas else "business growth"
        offering = offerings[0] if offerings else "product optimization"
        trend = trends[0] if trends else "industry trend"

        self.use_cases = [
            f"AI for improving {focus_area}",
            f"ML to optimize {offering}",
            f"GenAI to address {trend}",
        ]
        return self.use_cases

    def refine_use_cases_with_gemini(self, use_cases, company_name, industry):
        if model is None:
            return use_cases

        prompt = f"""Given the company '{company_name}' in the '{industry}' industry,
refine the following AI use case ideas into more specific, impactful, and innovative suggestions:
{', '.join(use_cases)}
Limit to 5 refined use cases."""

        try:
            response = model.generate_content(prompt)
            if hasattr(response, 'text'):
                refined = [line.strip('- ') for line in response.text.split('\n') if line.strip()]
                return refined[:5]
            else:
                st.warning("Gemini did not return properly.")
                return use_cases
        except Exception as e:
            st.error(f"Error refining use cases: {e}")
            return use_cases

class ResourceAgent:
    def __init__(self):
        self.datasets = {}

    def find_datasets(self, use_cases):
        for use_case in use_cases:
            try:
                results = list(search(f"{use_case} dataset", num_results=1, lang="en"))
                self.datasets[use_case] = results[0] if results else "No dataset found"
            except Exception:
                self.datasets[use_case] = "No dataset found"
        return self.datasets

    def save_resources(self, datasets, filename="resources.txt"):
        try:
            with open(filename, "w", encoding="utf-8") as f:
                for use_case, link in datasets.items():
                    f.write(f"Use Case: {use_case}\nDataset Link: {link}\n\n")
            return True
        except Exception as e:
            st.error(f"Error saving resources: {e}")
            return False

class ProposalAgent:
    def __init__(self):
        self.final_proposal = ""

    def create_proposal(self, company_info, refined_use_cases, datasets, industry_info):
        self.final_proposal = f"""
**AI/GenAI Use Case Proposal**

**Company Research Source:** {company_info.get('url', 'N/A')}
**Industry Research Source:** {industry_info.get('url', 'N/A')}

**Company Information:**
- Offerings: {company_info.get('offerings', 'N/A')}
- Focus Areas: {company_info.get('focus_areas', 'N/A')}

**Industry Information:**
- Trends: {industry_info.get('trends', 'N/A')}
- Standards: {industry_info.get('standards', 'N/A')}

**Refined AI Use Cases:**
"""
        for i, use_case in enumerate(refined_use_cases):
            self.final_proposal += f"{i+1}. {use_case} (Dataset: {datasets.get(use_case, 'N/A')})\n"
        return self.final_proposal

    def save_proposal(self, final_proposal, filename="proposal.txt"):
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(final_proposal)
            return True
        except Exception as e:
            st.error(f"Error saving proposal: {e}")
            return False

# --- Streamlit App ---

def main():
    st.title("🚀 AI Use Case Generator (Gemini-powered)")
    
    company_name = st.text_input("Enter Company Name:")
    industry = st.text_input("Enter Industry:")

    if st.button("Generate AI Use Cases"):
        with st.spinner("Processing..."):
            research_agent = ResearchAgent()
            company_info = research_agent.research_company(company_name)
            industry_info = research_agent.research_industry(industry)

            use_case_agent = UseCaseAgent()
            initial_use_cases = use_case_agent.generate_use_cases(company_info, industry_info)

            refined_use_cases = use_case_agent.refine_use_cases_with_gemini(
                initial_use_cases, company_name, industry
            )

            resource_agent = ResourceAgent()
            datasets = resource_agent.find_datasets(refined_use_cases)
            resource_saved = resource_agent.save_resources(datasets)

            proposal_agent = ProposalAgent()
            final_proposal = proposal_agent.create_proposal(
                company_info, refined_use_cases, datasets, industry_info
            )
            proposal_saved = proposal_agent.save_proposal(final_proposal)

        if proposal_saved and resource_saved:
            st.success("🎯 AI Use Cases Generated and Saved!")
            st.download_button("Download Proposal", final_proposal, file_name="proposal.txt")
            resources_text = "\n\n".join([f"Use Case: {k}\nDataset: {v}" for k, v in datasets.items()])
            st.download_button("Download Resources", resources_text, file_name="resources.txt")

            st.subheader("Final Proposal")
            st.write(final_proposal)
        else:
            st.error("Error generating or saving files.")

if __name__ == "__main__":
    main()
