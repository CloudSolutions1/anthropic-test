import os
# from dotenv import load_dotenv, find_dotenv
# from langchain.llms import GooglePalm
from langchain.vectorstores import FAISS
# from langchain.embeddings import GooglePalmEmbeddings
from langchain.chains import RetrievalQA
from langchain.chat_models import ChatOpenAI
# from langchain.llms import AzureOpenAI
# from langchain.document_loaders import DirectoryLoader,PyPDFLoader
# from langchain.document_loaders import UnstructuredExcelLoader
# from langchain.vectorstores import DocArrayInMemorySearch
from langchain.memory import ConversationBufferMemory
# from IPython.display import display, Markdown
# import pandas as pd
# import gradio as gr
# from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain import PromptTemplate
# from langchain.vectorstores import Chroma
# from langchain.agents.tools import Tool
# from langchain.experimental.plan_and_execute import PlanAndExecute, load_agent_executor, load_chat_planner
# from langchain import OpenAI, VectorDBQA
# from langchain.chains.router import MultiRetrievalQAChain
import streamlit as st
# from langchain.document_loaders import UnstructuredPDFLoader
# _ = load_dotenv(find_dotenv())


session = st.session_state
if 'transcript' not in session:
    session.transcript = []

if 'analysis' not in session:
    session.analysis = []

if 'input_disabled' not in session:
    session.input_disabled = True

if 'analyze_disabled' not in session:
    session.analyze_disabled = False

os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
llm = ChatOpenAI(model_name="gpt-3.5-turbo-16k", temperature=0.1)
embeddings = OpenAIEmbeddings(model="text-embedding-ada-002",chunk_size =1)

template = """
You are a helpful virtual assistant of OSFI. Analyze the context and answer the question in "Yes" or "No" only. Remember the
answer should be only "Yes" or "No". If you don't know the answer, just answer "No".
Use the following context (delimited by <ctx></ctx>) to answer the question:

------
<ctx>
{context}
</ctx>
------
{question}
Answer:
"""

prompt = PromptTemplate(input_variables=["context", "question"],template=template)

def get_answer(question):
    agent = RetrievalQA.from_chain_type(llm = llm,
        chain_type='stuff', # 'stuff', 'map_reduce', 'refine', 'map_rerank'
        retriever=bank_db.as_retriever(),
        verbose=False,
        chain_type_kwargs={
        "verbose":True,
        "prompt": prompt,
        "memory": ConversationBufferMemory(
            input_key="question"),
    })
    return agent.run(question)

def updated_analysis(message):
    session.analysis.append(message)
    analysis_container.write(message)

institute_names = {"BMO":"bmo_ar2022 (2)_index","NBC":"NATIONAL BANK OF CANADA_ 2022 Annual Report (1)_index"}

with st.sidebar:
    institute = st.selectbox(label="Institute",options=institute_names)
    analyze_button = st.empty()
    analysis_container = st.container()


    q1 = f"Does {institute} have a parent company?"
    q1y_list = [
        f"Is {institute}'s parent an operating company regulated by OSFI?",
        f"Has {institute}'s parent adopted an internal rating (IRB) approach to credit risk?",
        f"Is {institute} a fully- consolidated subsidiary?",
        f"Does {institute} have at least 95% of its credit risk exposures captured under the IRB approach?"
        ]
    q1n_list = [
        f"Has {institute} adopted an internal rating (IRB) approach to credit risk?",
        f"Is {institute} a fully- consolidated subsidiary?",
        f"Does {institute} have at least 95% of its credit risk exposures captured under the IRB approach?"
        ]
    q2 = f"Is {institute} reporting less than $10 billion in total assets?"
    q2y_list = [
        f"Is {institute} reporting greater than $100 million in total loans?",
        f"Does {institute} have an interest rate or foreign exchange derivatives with a combined notional amount greater than 100% of total capital?",
        f"Does {institute} have any other types of derivative exposure?",
        f"Does {institute} have exposure to other off-balance sheet items greater than 100% of total capital?"
        ]
    
    def analyze():
        with st.spinner():
            session.analyze_disabled = True
            updated_analysis("The first step is to figure out whether the institute belong to BCAR Short Form, Category III or Full BCAR category.\n\nTo determine which of the above category the institute belongs to you need to answer a series of questions.")
            q1_ans = get_answer(q1)
            updated_analysis(q1_ans)
            institute_type = "Short Form"
            possibly_cat3 = False
            if q1_ans.startswith("Yes"):
                for qs in q1y_list:
                    updated_analysis(qs)
                    qs_ans = get_answer(qs)
                    updated_analysis(qs_ans)      
                    if qs_ans.startswith("No"):
                        possibly_cat3 = True
                        break
            elif q1_ans.startswith("No"):
                for qs in q1n_list:
                    updated_analysis(qs)
                    qs_ans = get_answer(qs)
                    updated_analysis(qs_ans)      
                    if qs_ans.startswith("No"):
                        possibly_cat3 = True
                        break
            if possibly_cat3:
                updated_analysis("Based on the answers of the above question the institude does not come under BCAR Short Form Category. We will now check if it comes under BCAR Category III")
                institute_type = "Category III"
                updated_analysis(q2)
                q2_ans = get_answer(q2)
                updated_analysis(q2_ans)
                if q2_ans.startswith("Yes"):
                    for qs in q2y_list:
                        updated_analysis(qs)
                        qs_ans = get_answer(qs)
                        updated_analysis(qs_ans)
                        if qs_ans.startswith("Yes"):
                            updated_analysis("Based on the answers of the above question the institude does not come under BCAR Short Form or BCAR Category II so it belongs to Full BCAR Category")
                            institute_type = "Full Form"
                            break
                        updated_analysis("Based on the answers of the above question the institude comes under BCAR Category III")
                else:
                    updated_analysis("Based on the answers of the above question the institude does not come under BCAR Short Form or BCAR Category II so it belongs to Full BCAR Category")
                    institute_type = "Full Form"
            else:
                updated_analysis("Based on the answers of the above question the institude comes under BCAR Short Form Category")
            session.input_disabled = False

    analyze_button.button("Analyze",use_container_width=True,disabled=session.analyze_disabled,on_click=analyze)
    bank_db = FAISS.load_local(folder_path='./FAISS_VS', embeddings=embeddings, index_name=institute_names[institute])


user_input = st.chat_input("Query",disabled=session.input_disabled)

