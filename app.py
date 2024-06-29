import openai
import time
import streamlit as st

def main():
    st.set_page_config(
        page_title="OpenAI Assistant with Retrieval",
        page_icon="📚",
    )

    api_key = st.secrets["OPENAI_API_KEY"]
    assistant_id = st.secrets["ASSISTANT_ID"]

    st.session_state.client = openai.OpenAI(api_key=api_key)

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "start_chat" not in st.session_state:
        st.session_state.start_chat = False

    if st.session_state.client:
        st.session_state.start_chat = True

    if st.session_state.start_chat:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        if prompt := st.chat_input(f"Message for more Tobacco Related Questions..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            try:
                st.session_state.thread = st.session_state.client.beta.threads.create()

                st.session_state.client.beta.threads.messages.create(
                    thread_id=st.session_state.thread.id,
                    role="user",
                    content=prompt,
                )

                run = st.session_state.client.beta.threads.runs.create(
                    thread_id=st.session_state.thread.id,
                    assistant_id=assistant_id,
                )

                def wait_for_complete(run, thread):
                    while run.status in ["queued", "in_progress"]:
                        run = st.session_state.client.beta.threads.runs.retrieve(
                            thread_id=thread.id,
                            run_id=run.id,
                        )
                        time.sleep(0.5)
                    return run

                run = wait_for_complete(run, st.session_state.thread)

                replies = st.session_state.client.beta.threads.messages.list(
                    thread_id=st.session_state.thread.id
                )

                def process_replies(replies):
                    citations = []

                    for r in replies:
                        if r.role == "assistant":
                            message_content = r.content[0].text
                            annotations = getattr(message_content, 'annotations', [])

                            for index, annotation in enumerate(annotations):
                                message_content.value = message_content.value.replace(
                                    annotation.text, f" [{index}]"
                                )

                                if file_citation := getattr(annotation, "file_citation", None):
                                    try:
                                        cited_file = st.session_state.client.files.retrieve(
                                            file_citation.file_id
                                        )
                                        quote = getattr(file_citation, "quote", "No quote available")
                                        citations.append(
                                            f"[{index}] {quote} from {cited_file.filename}"
                                        )
                                    except AttributeError as e:
                                        st.error(f"Error retrieving file citation: {e}")
                                elif file_path := getattr(annotation, "file_path", None):
                                    try:
                                        cited_file = st.session_state.client.files.retrieve(
                                            file_path.file_id
                                        )
                                        citations.append(
                                            f"[{index}] Click <here> to download {cited_file.filename}"
                                        )
                                    except AttributeError as e:
                                        st.error(f"Error retrieving file path: {e}")

                    full_response = message_content.value + "\n" + "\n".join(citations)
                    return full_response

                processed_response = process_replies(replies)
                st.session_state.messages.append(
                    {"role": "assistant", "content": processed_response}
                )

                with st.chat_message("assistant"):
                    st.markdown(processed_response, unsafe_allow_html=True)

            except Exception as e:
                st.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()

