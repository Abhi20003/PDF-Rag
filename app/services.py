import os
import PyPDF2
from chromadb import PersistentClient
from dotenv import load_dotenv
from fastapi import HTTPException
from groq import Groq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
import re

# client = OpenAI(api_key=os.getenv("OPENROUTER_API_KEY"), base_url="https://api.deepseek.com")
load_dotenv()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"),)

embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
chroma_client = PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection("pdf_chunks")




def upload_file(files):
    for file in files:
        text = extract_text_from_pdf(file)
        text_chunks = split_text(text)

        embeddings = embedding_model.embed_documents(text_chunks)
        
        collection.add(
            ids=[f"{file.filename}_{i}" for i in range(len(text_chunks))], 
            embeddings=embeddings,
            documents=text_chunks,
            metadatas=[{"source": file.filename, "chunk_index": i} for i in range(len(text_chunks))]
        )

        important_text = rank_sentences_by_tfidf(text, max_sentences=80)
        
        prompt = f"""
            Give me a detailed summary of this content that has been extracted from the pdf. Only use this information to give the answer.

            Content {important_text}
        """
        response = queryLlm(prompt).content

        # print(response)

    return {"message": "Documents added to vector store", "summary": response}

def query_rag_model(request, conversation_history):
    query_analysis_prompt = f"""
        Analyze the user's query and determine its category:
        - If it's greeting like Hi, Hello, I am good, return "greeting".
        - If it's about any information or any facts, summary or explanantion, what, when who any question, return "document".

        Just return a the single word and nothing else.

        Query: {request.query}
    """
    
    query_category = queryLlm(query_analysis_prompt).content.strip().lower()
    print(query_category)

    if query_category == "greeting":
        return {"response": queryLlm(f"Respond naturally: {request.query}").content.strip()}

    document_chunks, sources = retrieve_relevant_chunks(embedding_model, collection, request.query)
    
    if not document_chunks:
        return {"response": "I couldn't find information related to this in the uploaded documents."}

    context = ""
    for i, chunk in enumerate(document_chunks):
        source = sources[i] if i < len(sources) else "Unknown Source"
        context += f"\n[Source: {source}]\n{chunk}\n"

    history_context = "\n".join([f"User: {entry['user']}\nModel: {entry['model']}" for entry in conversation_history[-2:]])

    print(context)
    
    prompt = f"""
        You must only answer using the provided context which is extracted from RAG of uploaded PDFs. Answer in proper English like how a human would respond.
        If the answer is not in the context, say: "I couldn't find information related to this in the uploaded documents." and just return this only.

        Don't write anything like "Based on the given context" or stuff, directly start writing the answer. 
        In the end mention the filename of the resource that has been used to return this answer. Note: If you dont use some content from specific chunk don't mention that in so
        Context: {context}
        Question: {request.query}

        Give a clear detailed helpful response.
    """

    response = queryLlm(prompt)
    finalResponse = response.content.strip()

    conversation_history.append({"user": request.query, "model": finalResponse})

    return {"response": finalResponse}

def extract_text_from_pdf(pdf_file):
    try:
        reader = PyPDF2.PdfReader(pdf_file.file)
        text = "".join([page.extract_text() or "" for page in reader.pages])
        return text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting text: {e}")


def split_text(text, chunk_size=1000, chunk_overlap=100):
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return splitter.split_text(text)

def queryLlm(prompt):
    messages = [
        {"role": "system", "content": "You must answer only using the given context."},
        {"role": "user", "content": prompt}
    ]

    chat_completion = client.chat.completions.create(
        messages=messages,
        model="llama3-70b-8192",
        stream=False,
    )
    response = chat_completion.choices[0].message
    print(response)
    
    return response

def retrieve_relevant_chunks(embedding_model, collection, query):
    query_embedding = embedding_model.embed_query(query)
    results = collection.query(query_embedding, n_results=5)

    documents = []
    sources = []

    for i, doc_chunks in enumerate(results["documents"]):
        for chunk in doc_chunks:
            documents.append(chunk)
            sources.append(results["metadatas"][i]) 
    return documents, sources

def rank_sentences_by_tfidf(text, max_sentences=30):
    """Extract the most important sentences using TF-IDF ranking."""
    sentences = split_sentences(text)
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(sentences)
    sentence_scores = np.array(tfidf_matrix.sum(axis=1)).flatten()
    
    # Rank sentences by importance
    ranked_sentences = [sentences[i] for i in sentence_scores.argsort()[-max_sentences:]]
    
    return " ".join(ranked_sentences)


def split_sentences(text: str):
    """Tokenize sentences using regex."""
    return re.split(r'(?<=[.!?])\s+', text.strip())
