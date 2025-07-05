from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import os
import google.generativeai as genai
from PIL import Image
from io import BytesIO
import re

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
st.set_page_config(page_title="Smart Calorie Estimator", page_icon="🍱", layout="centered")

st.title("🍱 Smart Calorie Estimator")

# ----------------- Prompt ---------------------
initial_prompt = """
You are a food image recognition expert. Look at the meal in the image and return the list of visible food items and an approximate per-serving calorie estimate like this:

1. **Food Name** – Approximate calories per serving  
Explain in 1 line how you identified it, if possible.
"""

def get_initial_food_items(image_parts, detection_prompt): # this function uses the Gemini model to detect food items in the image
    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content([detection_prompt, image_parts[0]]) # the model generates content based on the prompt and the image data
    # image_parts[0] is the image data, detection_prompt is the prompt to detect food items , 0 as the index of the first image part 
    # we pass only the first image part because we are only uploading one image
    return response.text # this returns the text response from the model which contains the detected food items and their calorie estimates

def get_calorie_estimate_with_quantities(food_data_prompt): # this function uses the Gemini model to estimate calories based on food items detected and their
    # quantities entered by the user
    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content(food_data_prompt)
    return response.text

def extract_food_items(text): # this function extracts food items from the text response returned by the model
    import re # re module is used for regular expression operations i.e., searching for patterns in the text
    # Try bold format first
    items = re.findall(r'\d+\.\s\*\*(.*?)\*\*', text) # It first attempts to extract items formatted with bold markdown syntax using the pattern
    if not items:
        # fallback: extract from lines like "1. Item Name -"
        items = re.findall(r'\d+\.\s(.*?)\s[-–]', text) # If the first pattern yields no results, the function falls back to a simpler format using 
        # r'\d+\.\s(.*?)\s[-–]'. This pattern captures items formatted like "1. Item Name -" or "1. Item Name –", where the food name appears between the 
        # number and a dash or en-dash.
    return [item.strip() for item in items] # The function returns a list of extracted items with whitespace stripped from each item using a list comprehension. 
# This cleaning step ensures that any leading or trailing spaces captured by the regex patterns are removed.


def input_image_setup(uploaded_file): # This function prepares the uploaded image for processing by the model
    return [{ # It returns a list with a dictionary containing the image data and its MIME type
        "mime_type": uploaded_file.type, # uploaded_file.type gives the MIME type of the uploaded file, e.g., "image/jpeg"
        "data": uploaded_file.getvalue() # uploaded_file.getvalue() reads the content of the uploaded file as bytes 
    }] # model can process image only in bytes format, so we convert the uploaded file to bytes using getvalue()


# ------------------ Upload and Detect ------------------
uploaded_file = st.file_uploader("📸 Upload your food image", type=["jpg", "jpeg", "png"])

if uploaded_file:
    st.image(Image.open(uploaded_file), caption="Uploaded Meal", use_container_width=True)

if "detection_result" not in st.session_state: # Initialize session state variables for storing detection results and food items
    st.session_state.detection_result = None # if detection_result is not in session state, set it to None
if "food_items" not in st.session_state: # Initialize food_items in session state to store detected food items
    st.session_state.food_items = [] # if food_items is not in session state, set it to an empty list

if uploaded_file and st.button("🔍 Detect Food Items"):
    with st.spinner("Detecting food items..."):
        image_data = input_image_setup(uploaded_file)
        detection_result = get_initial_food_items(image_data, initial_prompt)
        st.session_state.detection_result = detection_result # Store the detection result in session state for later use
        st.session_state.food_items = extract_food_items(detection_result) # Extract food items from the detection result and store them in session state

# ------------------ Show Detection + Quantity Input ------------------
if st.session_state.detection_result: # from session state, we check if detection_result is not None, if it is not None, we display the detected food items 
    # and allow the user to input quantities
    st.subheader("🍽️ Detected Items")
    st.markdown(st.session_state.detection_result, unsafe_allow_html=True) # Display the detection result with HTML rendering

    st.subheader("✏️ Enter Quantity for Each Item")

    quantity_inputs = {} # Dictionary to store user inputs for quantities of each food item
    with st.form("quantity_form"): # Create a form for quantity inputs
        for item in st.session_state.food_items: # Iterate over each detected food item and create a text input for quantity
            quantity = st.text_input(f"How much **{item}**? (e.g., '1 bowl', '100g', '2 pcs')", key=f"qty_{item}")
            quantity_inputs[item] = quantity
        submit_qty = st.form_submit_button("✅ Calculate Total Calories")

    if submit_qty: # When the user submits the form, we process the quantities
        prompt = "Estimate calories for the following items and quantities:\n\n"
        for item, qty in quantity_inputs.items(): # Iterate over the quantity inputs and format them for the prompt
            if qty.strip(): # Check if the quantity input is not empty by stripping whitespace
                prompt += f"- {item}: {qty.strip()}\n" # Add the item and its quantity to the prompt one by one using a bullet point format
        prompt += "\nReturn a list with:\n1. Item – Calories\nTotal Calories: xxx" # Add instructions for the model to return a list of items with their calorie estimates and a total calorie count

        with st.spinner("Calculating calories based on quantities..."):
            response = get_calorie_estimate_with_quantities(prompt)
            st.subheader("📊 Final Calorie Estimate")
            st.markdown(response, unsafe_allow_html=True)

            # Download button
            buffer = BytesIO() # Create a BytesIO buffer to hold the response text
            buffer.write(response.encode()) # Write the response text to the buffer
            buffer.seek(0) # Reset the buffer position to the beginning for reading
            st.download_button("💾 Download Result", data=buffer, file_name="final_calorie_report.txt", mime="text/plain")
            # Display the download button for the user to download the result as a text file and set the MIME type to "text/plain" 
            # data is the buffer containing the response text, file_name is the name of the file to be downloaded, and mime is the MIME type of the file
