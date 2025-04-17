import requests
from bs4 import BeautifulSoup
import streamlit as st
import json
import os

def load_config():
    
    config = {}
   
    config['llm_api_key'] = "hf_khqbnxfosAnjemNeqNbqLZAYSaWfHcxu"  #  Replace with a real free API key
    if not config['llm_api_key']:
        st.error("LLM API key not found.  Please add a valid LLM API key to the code.")
        st.stop()
    return config

# Load the configuration
config = load_config()

# 2. Web Scraping Function

def scrape_website(url):
    
    try:
        
        response = requests.get(url, timeout=10)
        
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        text = soup.get_text(separator=' ', strip=True)
        return text
    except requests.exceptions.RequestException as e:
        
        st.error(f"Error fetching URL {url}: {e}")
        return None
    except Exception as e:
        
        st.error(f"An unexpected error occurred while scraping {url}: {e}")
        return None

# 3. LLM Interaction Function
# ----------------------------
#    -  This function takes the extracted text from a website and
#       sends it to the LLM API.

def get_product_data_from_llm(text, llm_api_key):
    """
    Extracts product data using Hugging Face Inference API (Falcon-7B-Instruct).

    Args:
        text (str): The input text from the website.
        llm_api_key (str): Your Hugging Face API key.

    Returns:
        dict or list: Extracted structured data (product list), or None on failure.
    """
    model_id =  "HuggingFaceH4/zephyr-7b-beta"
    api_url = f"https://api-inference.huggingface.co/models/{model_id}"

    headers = {
        "Authorization": f"Bearer {llm_api_key}",
        "Content-Type": "application/json"
    }

    prompt = f"""
You are an intelligent agent that extracts structured crop product information from e-commerce website text.

Extract a list of hydroponic vegetable or seed products and their prices from the following text:
{text[:1000]}

Return only a JSON array of products. Each product should have:
- "product" (name of product)
- "price_per_kg" (price in INR per kg or closest unit)
- "demand_category" (High, Medium, Low) — optional based on price/commonality

Do not include any explanation or natural language. Only output pure JSON.
"""

    payload = {
    "inputs": prompt,
    "parameters": {
        "return_full_text": False  # Ensure output is ONLY the generated part
    },
    "options": {
        "wait_for_model": True
    }
    }


    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        generated_text = response.json()[0]["generated_text"]


        json_start = generated_text.find('[')
        json_end = generated_text.rfind(']') + 1
        json_data = generated_text[json_start:json_end]

        return json.loads(json_data)

    except requests.exceptions.RequestException as e:
        st.error(f"Hugging Face API request error: {e}")
    except json.JSONDecodeError as e:
        st.error(f"Failed to parse JSON from Hugging Face response: {e}\nResponse was:\n{generated_text}")
    except Exception as e:
        st.error(f"Unexpected error: {e}")

    return None




# 4. Main Application Logic

def main():
    """
    Main function to run the crop data extraction application.
    """
    st.title("Crop E-commerce Data Extractor")

   
    urls_input = st.text_area(
        "Enter URLs (one per line):",
        "https://www.bluelettuce.in/our-products/\nhttps://onlyhydroponics.in/collections/herbs\nhttps://www.jagsfresh.com/subcategory/vegetables/hydroponics",
    )
   
    urls = [url.strip() for url in urls_input.splitlines() if url.strip()]


    if st.button("Extract Data"):
        results = []
        
        for url in urls:
            
            website_name = url.split("//")[-1].split("/")[0]
            st.info(f"Processing URL: {url}") 
            text = scrape_website(url)
            if text:  
                product_data = get_product_data_from_llm(text, config['llm_api_key'])
                if product_data:
                    #  Append the result to the list.
                    results.append({"website": website_name, "products": [product_data]})
                else:
                  results.append({"website": website_name, "products": []}) # add empty list
            else:
                st.error(f"Failed to scrape data from {url}. Skipping.")
                results.append({"website": website_name, "products": []})

        #  Display the results.
        st.subheader("Extracted Data:")
        st.json(results)

        #  Display the results in a table for better readability.
        st.subheader("Tabular View:")
        for website_result in results:
            st.write(f"**{website_result['website']}**")
            if website_result['products']:
                st.table(website_result["products"])
            else:
                st.write("No products found on this website.")

# 5. Run the Application
if __name__ == "__main__":
    main()