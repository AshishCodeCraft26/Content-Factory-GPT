import streamlit as st
import os
from groq import Groq
from dotenv import load_dotenv
import textwrap
import pandas as pd
import re

from langchain.chains import ConversationChain
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from itertools import product
from stqdm import stqdm
import base64
from io import BytesIO

load_dotenv()

groq_api_key = os.getenv("GROQ_API_KEY")


def get_prompt():

    system = "You are a helpful assistant."

    human = "{text}"
    prompt_template = ChatPromptTemplate.from_messages([("system", system), ("human", human)])

    return prompt_template

def cut_off_text(text, prompt):
    cutoff_phrase = prompt
    index = text.find(cutoff_phrase)
    if index != -1:
        return text[:index]
    else:
        return text

def remove_substring(string, substring):
    return string.replace(substring, "")

def generate(model, human_text):

    prompt_template = get_prompt()

    groq_chat = ChatGroq(
            groq_api_key=groq_api_key, 
            model_name=model,
            temperature=0.1,
    )
    chain = prompt_template | groq_chat
    output = chain.invoke({"text": f"{human_text}"})

    return output

def parse_text(generated_text):
        generated_text = generated_text.content
        wrapped_text = textwrap.fill(generated_text, width=100)
        return wrapped_text


st.set_page_config(layout='wide',
                   page_title="Content Factory")



def clean_string(text):
        # Use a regular expression to match various whitespace characters
        whitespace_pattern = re.compile(r'\s+')

        # Substitute the whitespace with a single space
        cleaned_text = whitespace_pattern.sub(' ', text)

        return cleaned_text

with st.sidebar:
     
    st.header('How to use :bulb:')
    st.markdown(":one:  Select the customer attributes and brand")
    st.markdown(":two:  Edit the brand statement :speech_balloon:")
    st.markdown(":three:  Upload a product detail excel file 📄")
    st.markdown(":four:  Click Generate Content after uploading the product file to commence content generation regarding the products. If you wish to halt the process midway, simply press the reset button.")
    st.markdown(":five:  Once the content generation is complete, you can download the generated content file. :inbox_tray:")

    


st.title(":robot_face: Content-Factory GPT")
st.markdown("Content-Factory transforms product details into tailored content for websites, social media, and ads. It saves time and resources by automating content generation, allowing for human review and approval. Experience the pinnacle of professional content creation with our innovative platform.")

for _ in range(1):
    st.write("")


col1, col2 = st.columns([1,5],gap='medium')

with col1:


    customer_attributes = {
    "Age" :["18-30", "31-45", "45-65","65+"],
    "Gender" : ["Male", "Female", "Others"]
    }

    selected_attributes = {}
    for attribute, options in customer_attributes.items():
        selected_option = st.selectbox(f"**{attribute}**", options)
        selected_attributes[attribute] = selected_option
        

with col2:


    brand_df = pd.read_excel('./Brand_Details.xlsx')
    brand_details = {'Brand': brand_df['Brand'].tolist()}

    for attribute, options in brand_details.items():
            col1,col2 = st.columns([1,3])
            with col1:
                selected_option = st.selectbox(f"**{attribute}**", options) 
            with col2:
                brand_statement = clean_string(brand_df.loc[brand_df['Brand'] == selected_option, 'Brand_Statement'].iloc[0])
                # Display the brand statement in an editable text input
                edited_brand_statement = st.text_area("**Brand Statement**", value=brand_statement, height=300)
            selected_attributes['Brand'] = selected_option
            selected_attributes['Brand_Statement'] = edited_brand_statement

for _ in range(1):
    st.write("")


# Upload a file
st.markdown("<h3 style='font-size: 20px;'>Upload a Product file and Generate Content</h3>", unsafe_allow_html=True)
uploaded_file = st.file_uploader("", type=["xlsx"])

if uploaded_file is not None:
    # Read the uploaded file
    if uploaded_file.name.endswith('.xlsx'):
        attribute_df = pd.read_excel(uploaded_file)
    else:
        # Handle other file types here
        pass
    
    
    model = 'llama3-70b-8192'
    # model = 'llama2-70b-4096'
    # model = 'Mixtral-8x7b-32768'

    main_headings = {}
    for _, row in attribute_df.iterrows():
        attribute = row['Attribute']
        options = row['Options'].split(',') if ',' in row['Options'] else [row['Options']]

        options = [option.strip() for option in options]

        main_headings[attribute] = options

    combinations = list(product(*main_headings.values()))

    intr_output_dir = 'Intermediate_Output'
    if not os.path.exists(intr_output_dir):
        os.makedirs(intr_output_dir)

    # Function to generate response based on selected attributes
    def generate_response(model, *selected_attributes):
        
        # Create an empty DataFrame to store the generated texts
        df = pd.DataFrame(columns=['Product', 'Gender','Size','Age','Color','Style','Feature','Brand','Material','Short Description','Long Description'])

        # result_li = []
        
        # Show processing animation
        with st.spinner("Content Generation in Progress...."):
            filename = f"{selected_attributes[0]['Brand']}_{selected_attributes[0]['Age']}_{selected_attributes[0]['Gender']}_generated_content.xlsx"
            with pd.ExcelWriter(os.path.join(intr_output_dir, filename), engine='xlsxwriter') as writer:
                for i, combo in enumerate(stqdm(combinations)):
                    Product, Color, Material, Size, Style, Feature = combo

                    user_prompt_short = f"Please generate a 200 character description for a {Product} for a {selected_attributes[0]['Gender']}, between the ages of {selected_attributes[0]['Age']}, the {Product} is {Color} in color, {Style}, with a {Feature}, the brand is {selected_attributes[0]['Brand']}, has a {Material} material, available in {Size} size. The description text is being used by a retailer promoting {selected_attributes[0]['Brand_Statement']}."
                    user_prompt_long = f"Please generate a 1024 character description for a {Product} for a {selected_attributes[0]['Gender']}, between the ages of {selected_attributes[0]['Age']}, the {Product} is {Color} in color, {Style}, with a {Feature}, the brand is {selected_attributes[0]['Brand']}, has a {Material} material, available in {Size} size. The description text is being used by a retailer promoting {selected_attributes[0]['Brand_Statement']}."
                    generated_text_short = parse_text(generate(model, user_prompt_short))
                    generated_text_long = parse_text(generate(model, user_prompt_long))
                    # result_li.append(generated_text)

                    
                    # Append the generated text directly to the DataFrame
                    df.loc[i] = [Product, selected_attributes[0]['Gender'], Size, selected_attributes[0]['Age'],Color, Style, Feature, selected_attributes[0]['Brand'], Material, generated_text_short, generated_text_long]

                    # Save the DataFrame to Excel file after each iteration
                    df.to_excel(writer, index=False)

                
        return df
    
    # Function to create a download link for Excel file
    def get_download_link(df, filename='generated_texts.xlsx'):

        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        excel_data = output.getvalue()
        b64 = base64.b64encode(excel_data).decode()
        href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}"><button style="font-weight:normal; border-radius: 8px; background-color: inherit; border: 1px solid #CCCCCC; padding: 5px 10px;">Download Generated Result</button></a>'
        return href

    def reset_session():
        # Clear session state
        st.session_state.clear()

        # Rerun the Streamlit app to reset everything
        st.rerun()

    col1, col2 = st.columns([1,2])
    with col1:
        if st.button("Generate Content"):
                
                df = generate_response(model, selected_attributes)
                st.success("Generation Completed Successfully!")

                filename = f"{selected_attributes['Brand']}_{selected_attributes['Age']}_{selected_attributes['Gender']}_generated_content.xlsx"

                # Display download link for the generated Excel file
                st.markdown(get_download_link(df,filename=filename), unsafe_allow_html=True) 

    with col2:
        st.button("Reset", type="primary")
        

            