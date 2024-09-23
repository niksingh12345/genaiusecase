from langchain_openai  import AzureChatOpenAI
from langchain_core.messages import SystemMessage,HumanMessage
import os
import streamlit as st
from io import StringIO
from dotenv import load_dotenv
load_dotenv()
azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
api_version = os.getenv("AZURE_OPENAI_API_VERSION")
api_key = os.getenv("AZURE_OPENAI_KEY")
model=os.getenv("AZURE_OPENAI_DEPLOYMENT")
chat =  AzureChatOpenAI(
    api_key=api_key,
    openai_api_version=api_version,
    azure_deployment=model,
    max_tokens=2000,
    temperature=0.7)
sys_msg="""You are motivational speaker and writes quotes for others"""
hum_msg=f""" Please give quote of the day"""
batch_message=[SystemMessage(content=sys_msg),HumanMessage(content=hum_msg)]
result=chat.invoke(batch_message)
        
st.set_page_config(
    page_title="Welcome to TAL",
    page_icon="C://Users//JU569XE//OneDrive - EY//Documents//poc_tal//input_text_file//TAL.png"
)
st.title("Convert Text file to CSV")
st.sidebar.success(result.content)
if "my_input" not in st.session_state:
    st.session_state["my_input"]=""

def create_csv_file():
    uploaded_files = st.file_uploader("Please choose a Text file", accept_multiple_files=True)

    for file in uploaded_files:
        bytes_data = file.read()
        stringio = StringIO(file.getvalue().decode("utf-8"))
        table = stringio.read()
        tablename = os. path. splitext(file.name)[0]
        sys_msg="""You are an experienced database engineer who wants to create a csv file & dummy data of columns based on the input provided to you."""
        hum_msg=f""" please create the csv file and dummy data of header.
        the table name is {tablename} and the columns with their data types and constraints are in {table}
        Save the header and all generated dummy data as a CSV file with the given {tablename}
        The .csv file generated should have only header and data
        Note - Be precise and omit the disclaimer & comments """
        batch_message=[SystemMessage(content=sys_msg),HumanMessage(content=hum_msg)]
        result=chat.invoke(batch_message)
        full_path=f"C://Users/JU569XE/OneDrive - EY/Documents/poc_tal/Output_csv_file/{tablename}.csv"
        with open(full_path,'w') as js:
            js.write(result.content)
        with open(full_path, 'rb') as f:
            st.download_button('Download CSV', f, file_name='claim.csv')


if __name__=="__main__":
    
    create_csv_file()