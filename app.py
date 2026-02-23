import gradio as gr
from concurrent.futures import ThreadPoolExecutor
from llm_functions import get_response_from_openai, get_gemini_response, get_claude_response

def query_all_llms(user_query):
    with ThreadPoolExecutor() as executor:
        f_openai = executor.submit(get_response_from_openai, user_query, [])
        f_gemini = executor.submit(get_gemini_response, user_query, [])
        f_claude = executor.submit(get_claude_response, user_query, [])
        return f_openai.result(), f_gemini.result(), f_claude.result()

def select_model(choice):
    if choice == "openai":
        return gr.update(visible=True), gr.update(visible=False), gr.update(visible=False)
    elif choice == "gemini":
        return gr.update(visible=False), gr.update(visible=True), gr.update(visible=False)
    else:
        return gr.update(visible=False), gr.update(visible=False), gr.update(visible=True)

with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🌍 Global Cost of Living AI Analyst")
    gr.Markdown("Compare cities, analyze rent, and plan your relocation with the power of 3 AI Models + Real Data.")
    with gr.Row():
        user_input = gr.Textbox(label="Enter your prompt", placeholder="Ask about the IIT Patna course...", scale=4)
        submit_btn = gr.Button("Query All Models", variant="primary", scale=1)

    with gr.Row() as comparison_row:
        with gr.Column(variant="panel") as col_openai:
            gr.Markdown("### OpenAI (via Groq)")
            openai_out = gr.Markdown("...")
            btn_openai = gr.Button("Continue with OpenAI")
        with gr.Column(variant="panel") as col_gemini:
            gr.Markdown("### Gemini")
            gemini_out = gr.Markdown("...")
            btn_gemini = gr.Button("Continue with Gemini")
        with gr.Column(variant="panel") as col_claude:
            gr.Markdown("### Claude (via HF)")
            claude_out = gr.Markdown("...")
            btn_claude = gr.Button("Continue with Claude")

    submit_btn.click(fn=query_all_llms, inputs=[user_input], outputs=[openai_out, gemini_out, claude_out])
    btn_openai.click(fn=lambda: select_model("openai"), outputs=[col_openai, col_gemini, col_claude])
    btn_gemini.click(fn=lambda: select_model("gemini"), outputs=[col_openai, col_gemini, col_claude])
    btn_claude.click(fn=lambda: select_model("claude"), outputs=[col_openai, col_gemini, col_claude])

if __name__ == "__main__":
    demo.launch()