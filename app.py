import streamlit as st
import pandas as pd
import openai
from io import BytesIO
from langchain_openai import AzureChatOpenAI
from langchain_openai import AzureOpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
import os
import time
import re

llm=AzureChatOpenAI(
    openai_api_key='aec3d951141348dfbd7d01ff7636b15d',
    deployment_name='gpt-35-turbo',
    api_version='2023-12-01-preview' ,     
    azure_endpoint='https://sakshiai.openai.azure.com/'
)
def read_excel(file):
    xls = pd.ExcelFile(file)
    sheet_names = xls.sheet_names
    return xls, sheet_names

def process_data(sheet_data):
    data_as_str = sheet_data.to_string()
    prompt_template = "Analyze the following data:\n{data}\n\nProvide a detailed analysis:"
    prompt = PromptTemplate(input_variables=["data"], template=prompt_template)
    llm_chain = LLMChain(prompt=prompt, llm=llm)
    response = llm_chain.run(data=data_as_str)
    return response

def translate_to_sql_condition(plain_text_condition):
    """
    Translates a plain English condition into SQL syntax.
    This is a simple implementation and may not cover all cases.
    """
    condition = plain_text_condition.strip().lower()
    
    # Simple replacements and transformations
    condition = condition.replace("is equal to", "=")
    condition = condition.replace("equals", "=")
    condition = condition.replace("is not equal to", "!=")
    condition = condition.replace("is greater than or equal to", ">=")
    condition = condition.replace("is less than or equal to", "<=")
    condition = condition.replace("is greater than", ">")
    condition = condition.replace("is less than", "<")
    condition = condition.replace("is between", "BETWEEN")
    condition = condition.replace("and", "AND")
    condition = condition.replace("or", "OR")
    
    # Remove unnecessary words
    unnecessary_words = ["value", "to", "from"]
    for word in unnecessary_words:
        condition = condition.replace(f" {word} ", " ")
    
    return condition

def validate_where_clause(where_clause):
    # Updated regex pattern to validate basic SQL WHERE clause including BETWEEN
    pattern = re.compile(r"""
        ^\s*
        (?:\w+(\.\w+)?)\s*                # Column Name
        (?:=|>|<|!=|>=|<=|BETWEEN)\s*   # Comparison Operator or BETWEEN
        (?:\w+|'\w+'|[\d\.]+)            # Value (number or string)
        (?:\s+AND\s+(?:\w+(\.\w+)?)\s*(?:=|>|<|!=|>=|<=|BETWEEN)\s*(?:\w+|'\w+'|[\d\.]+))* # Additional Conditions
        \s*$
    """, re.IGNORECASE | re.VERBOSE)
    return pattern.match(where_clause) is not None

def generate_sql_query_with_join(sheet1_data, sheet2_data, table1_name, table2_name, join_columns, select_columns, aggregate_functions, join_type, where_clause):
    # Construct the JOIN clause
    join_clause = f"{join_type} {table2_name} ON " + " AND ".join(
        [f"{table1_name}.{col} = {table2_name}.{col}" for col in join_columns]
    )
    
    # Handle aggregate functions in the SELECT clause
    select_clause_parts = []
    group_by_columns = set()
    aggregate_columns = set()

    for column, agg_func in zip(select_columns, aggregate_functions):
        if agg_func:  # If an aggregate function is specified, use it
            select_clause_parts.append(f"{agg_func}({column}) AS {agg_func.lower()}_{column}")
            aggregate_columns.add(column)
        else:  # Otherwise, just use the column name
            select_clause_parts.append(column)
            group_by_columns.add(column)
    
    select_clause = ", ".join(select_clause_parts)

    # Automatically add GROUP BY clause based on the columns in the SELECT clause
    if aggregate_columns:
        # Include non-aggregated columns in GROUP BY
        group_by_columns.update(
            col for col in select_columns if col not in aggregate_columns
        )
        group_by_clause = "GROUP BY " + ", ".join(group_by_columns)
    else:
        group_by_clause = ""
    
    # Translate and validate the WHERE clause
    if where_clause:
        translated_where_clause = translate_to_sql_condition(where_clause)
        if validate_where_clause(translated_where_clause):
            where_clause = f"WHERE {translated_where_clause}"
        else:
            st.error("The WHERE clause is not a valid SQL condition.")
            where_clause = ""
    else:
        where_clause = ""
    
    # Combine clauses into the final SQL query
    sql_query = (
        f"SELECT {select_clause} "
        f"FROM {table1_name} {join_clause} "
        f"{where_clause} "
        f"{group_by_clause};"
    )
    
    return sql_query

def ask_question_about_data(sheet_data, question, llm):
    data_as_str = sheet_data.to_string()
    prompt_template = (
        "Based on the following data:\n{data}\n\n"
        "Question: {question}\n\n"
        "Answer:"
    )
    prompt = PromptTemplate(input_variables=["data", "question"], template=prompt_template)
    llm_chain = LLMChain(prompt=prompt, llm=llm)
    response = llm_chain.run(data=data_as_str, question=question)
    return response

# Streamlit App
st.title('Excel Sheet Reader and Analyzer')

uploaded_file = st.file_uploader("Choose an Excel file", type="xlsx")

if uploaded_file is not None:
    xls, sheet_names = read_excel(uploaded_file)
    selected_sheets = st.multiselect('Select sheets to analyze', sheet_names)

    if selected_sheets:
        for sheet in selected_sheets:
            st.write(f"### Analysis for sheet: {sheet}")
            sheet_data = pd.read_excel(xls, sheet_name=sheet)
            st.write(sheet_data)
            analysis_result = process_data(sheet_data)
            st.write("Analysis Result:", analysis_result)

    else:
        st.info("Please select at least one sheet for analysis.")
    
    sheet1 = st.selectbox('Select the first sheet', sheet_names)
    sheet2 = st.selectbox('Select the second sheet to join', sheet_names)
    
    if sheet1 and sheet2:
        sheet1_data = pd.read_excel(xls, sheet_name=sheet1)
        sheet2_data = pd.read_excel(xls, sheet_name=sheet2)
        
        join_columns = st.multiselect('Select columns to join on', sheet1_data.columns.intersection(sheet2_data.columns))
        
        # Provide a list of columns to select from for the SELECT clause
        available_columns = sheet1_data.columns.union(sheet2_data.columns).tolist()
        select_columns = st.multiselect('Select columns for SELECT clause', available_columns)
        
        # Allow users to specify aggregate functions if needed
        aggregate_functions = []
        for column in select_columns:
            agg_func = st.selectbox(f'Select aggregate function for column {column} (or none)', ['', 'SUM', 'AVG', 'COUNT', 'MAX', 'MIN'])
            aggregate_functions.append(agg_func)

        # Allow users to select the type of join
        join_type = st.selectbox('Select join type', ['INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'FULL JOIN'])
        
        # Prompt for WHERE clause
        where_clause = st.text_input('Enter SQL condition for WHERE clause (in plain English or SQL syntax)')

        if st.button('Generate SQL Query'):
            if join_columns and select_columns:
                sql_query = generate_sql_query_with_join(
                    sheet1_data, sheet2_data,
                    table1_name=sheet1, table2_name=sheet2,
                    join_columns=join_columns,
                    select_columns=select_columns,
                    aggregate_functions=aggregate_functions,
                    join_type=join_type,
                    where_clause=where_clause
                )
                st.write("Generated SQL Query:", sql_query)
            else:
                st.error("Please select join columns and columns to include in the output.")

    # Ask a question about the data
    question = st.text_input('Ask a question about the data:')
    if question:
        if sheet1_data is not None:
            answer = ask_question_about_data(sheet1_data, question, llm)
            st.write("Question:", question)
            st.write("Answer:", answer)
        else:
            st.error("Please select a sheet to analyze before asking questions.")