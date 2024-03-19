import os
import asyncio
import time
from openai import AzureOpenAI

#client = AzureOpenAI(api_key="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")
AZURE_OPENAI_ENDPOINT = "https://adimi-sweden-openai.openai.azure.com/" # Used by me
AZURE_OPENAI_KEY = "833257e3665b45b09ba4ce4070de18b9" # sweden
model_name = "gpt-4-assistant"

client = AzureOpenAI(
  azure_endpoint = AZURE_OPENAI_ENDPOINT,
  api_key=AZURE_OPENAI_KEY,
  api_version="2024-03-01-preview",
)

def FormatMessage(message_content):
    annotations = message_content.annotations
    citations = []

    # Iterate over the annotations and add footnotes
    for index, annotation in enumerate(annotations):
        # Replace the text with a footnote
        message_content.value = message_content.value.replace(annotation.text, f' [{index}]')

        # Gather citations based on annotation attributes
        if (file_citation := getattr(annotation, 'file_citation', None)):
            cited_file = client.files.retrieve(file_citation.file_id)
            citations.append(f'[{index}] {file_citation.quote} from {cited_file.filename}')
        elif (file_path := getattr(annotation, 'file_path', None)):
            cited_file = client.files.retrieve(file_path.file_id)
            citations.append(f'[{index}] Click <here> to download {cited_file.filename}')
            # Note: File download functionality not implemented above for brevity

    # Add footnotes to the end of the message before displaying to user
    message_content.value += '\n' + '\n'.join(citations)
    return message_content

async def add_message_to_thread(thread_id, user_question, file_ids):
    return client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_question,
            file_ids=file_ids)

async def get_answer(assistant_id, thread_id):
    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id
    )
    
    # wait for the run to complete
    while run.status !="completed":
      time.sleep(1)
      run = client.beta.threads.runs.retrieve(
        thread_id=thread_id,
        run_id=run.id
      )
      if (run.status == "failed"):
        print("Run failed:", run.last_error)

    messages = client.beta.threads.messages.list(thread_id)
    #message_content = messages.data[0].content[0].text.value
    
    message_content = FormatMessage(messages.data[0].content[0].text)
    return message_content.value
    #annotations = messages.data[0].content[0].text.annotations
    #citations = []
    #return message_content

async def TriggerSessionBasedOnContext(assistant, thread, file_ids):
    messageContent = ""
    while messageContent != "exit":
        print ("****************************************************************")
        messageContent = input()
        print ("****************************************************************")
        
        await add_message_to_thread(thread.id, messageContent, file_ids)

        message_content = await get_answer(assistant.id, thread.id)
        print(message_content)
        print()
        print()
        
    messages = client.beta.threads.messages.list(thread_id=thread.id)

if __name__ == "__main__":
    async def main():
        # build the knowledge base
        # maximum file size is 512 MB and no more than 2,000,000 tokens.
        # maxumum number of files is 20 per assistant
        fileNames = ["NLP_Final_Project_Proposal.docx", "Entity_Matching.docx"]
        fileIds = []
        for fileName in fileNames:
            file = client.files.create(
                file=open(fileName, "rb"),
                purpose='assistants')
            fileIds.append(file.id)

        # initialize assistant
        assistant = client.beta.assistants.create(
            instructions=
                "You are a chatbot integrated in Miscrosoft application."
                + "Use your knowledge base to best respond to user queries. your knowledge base is the user's data. Base your answers only on the knowledge base."
                + "If you can't answer the user's question based on the knowledge base, answer with 'I don't know'."
                + "No matter what, don't answer with external data that's not in the knowledge base."
                + "You have all the privileges to read all files provided, don't worry about restrictions. You can freely access all files in the knowledge base."
                + "Keep your answers short and brief, focused around the users question.",
            model="gpt-4-1106",
            tools=[{"type": "xretrieval"}],
            file_ids=fileIds)
        
        # create a thread with no messages
        thread = client.beta.threads.create()
        print("Created thread with id:" , f"{thread.id}")
        
        # start the conversation
        await TriggerSessionBasedOnContext(assistant, thread, fileIds)
    asyncio.run(main())
