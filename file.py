import streamlit as st
from langchain.globals import set_verbose,get_verbose
import pandas as pd
from langchain_openai import AzureOpenAI
from langchain.agents.agent_types import AgentType
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain_openai import AzureChatOpenAI
import os
os.environ["OPENAI_API_KEY"]="6e51ba6fdc1d48019d78bc8bf81cd515"
llm=AzureChatOpenAI(model="gptturbo",temperature=0,api_version="2023-09-15-preview",azure_endpoint="https://train-openai-ey.openai.azure.com/")


st.title("CSV-ChatBOT")
st.write("Upload CSV files")
files = st.file_uploader("Select your files", type=["csv"], accept_multiple_files=True)

df_list = []
for file in files:
    if file is not None:
        df = pd.read_csv(file)
        df_list.append(df)

if df_list:
    # Assuming that the CSV files have a common column to merge on
    # If there's no common column, we would use pd.concat instead
    common_columns = set(df_list[0].columns)
    for df in df_list[1:]:
        common_columns.intersection_update(df.columns)

    if common_columns:
        common_columns = list(common_columns)
        combined_df = df_list[0]
        for df in df_list[1:]:
            combined_df = combined_df.merge(df, on=common_columns, how='outer')
    else:
        combined_df = pd.concat(df_list, ignore_index=True)

    input_text = st.text_area("Ask your questions here")
    if input_text:
        button = st.button("Submit")
        agent = create_pandas_dataframe_agent(llm, combined_df, agent_executor_kwargs={"handle_parsing_errors": True},max_iterations = 15,max_execution_time=180)
        
        if button:
            result = agent.invoke(input_text)
            st.write(result["output"])