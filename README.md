# Pertamina_Chatbot

## Sebuah Chatbot untuk mempermudah proses pengadaan dalam Pertamina Patra Niaga

### Cara menjalankan proyek ini

'''bash
docker run --name pgvector-container -e POSTGRES_USER=langchain -e POSTGRES_PASSWORD=langchain -e POSTGRES_DB=langchain -p 5432:5432 -d pgvector/pgvector:pg16
'''

'''bash
uv run streamlit run streamlit_app
'''
