"""
Analytical Dashboard Q&A Chatbot using Gradio
"""
import gradio as gr
import plotly.graph_objects as go
import plotly.express as px
from orchestrator_agent import OrchestratorAgent
from adk_orchestrator import ADKOrchestratorAgent
from config import Config
import json
import os

# Initialize config and agent
config = Config()

# Use ADK agent if USE_ADK environment variable is set, otherwise use SDK agent
use_adk = os.getenv('USE_ADK', 'false').lower() == 'true'

if use_adk:
    agent = ADKOrchestratorAgent(config)
    print("✅ Using ADK Orchestrator Agent")
else:
    agent = OrchestratorAgent(config)
    print("✅ Using SDK Orchestrator Agent")

def create_membership_chart(data, signals):
    """Create membership comparison chart"""
    if not data or not signals:
        return None
    
    prior = data.get('prior_members', 0)
    current = data.get('current_members', 0)
    dropped = signals.get('dropped_mbr_cnt', 0)
    new_members = signals.get('new_mbr_cnt', 0)
    
    if prior == 0 and current == 0:
        return None
    
    fig = go.Figure()
    
    # Bar chart for prior vs current
    fig.add_trace(go.Bar(
        x=['Prior Period', 'Current Period'],
        y=[prior, current],
        name='Membership',
        marker_color=['#1f77b4', '#ff7f0e'],
        text=[f'{prior:,}', f'{current:,}'],
        textposition='auto'
    ))
    
    fig.update_layout(
        title='Membership Overview',
        yaxis_title='Number of Members',
        xaxis_title='Period',
        template='plotly_white',
        height=300,
        showlegend=False
    )
    
    return fig

def create_movement_chart(signals):
    """Create member movement chart"""
    if not signals:
        return None
    
    dropped = signals.get('dropped_mbr_cnt', 0)
    new_members = signals.get('new_mbr_cnt', 0)
    
    if dropped == 0 and new_members == 0:
        return None
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=['Dropped Members', 'New Members'],
        y=[dropped, new_members],
        marker_color=['#d62728', '#2ca02c'],
        text=[f'{dropped:,}', f'{new_members:,}'],
        textposition='auto'
    ))
    
    fig.update_layout(
        title='Member Movement',
        yaxis_title='Number of Members',
        template='plotly_white',
        height=250,
        showlegend=False
    )
    
    return fig

def format_metrics(data, signals):
    """Format key metrics as HTML"""
    if not data or not signals:
        return "No data available"
    
    prior = data.get('prior_members', 0)
    current = data.get('current_members', 0)
    net_change = signals.get('net_change', 0)
    dropped = signals.get('dropped_mbr_cnt', 0)
    new_members = signals.get('new_mbr_cnt', 0)
    dropped_per = signals.get('dropped_per', 0)
    new_per = signals.get('new_per', 0)
    
    change_color = '#2ca02c' if net_change >= 0 else '#d62728'
    change_icon = '📈' if net_change >= 0 else '📉'
    
    html = f"""
    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 20px 0;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 10px; color: white; text-align: center;">
            <div style="font-size: 14px; opacity: 0.9;">Prior Period</div>
            <div style="font-size: 32px; font-weight: bold; margin-top: 10px;">{prior:,}</div>
        </div>
        <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 20px; border-radius: 10px; color: white; text-align: center;">
            <div style="font-size: 14px; opacity: 0.9;">Current Period</div>
            <div style="font-size: 32px; font-weight: bold; margin-top: 10px;">{current:,}</div>
        </div>
        <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); padding: 20px; border-radius: 10px; color: white; text-align: center;">
            <div style="font-size: 14px; opacity: 0.9;">Net Change {change_icon}</div>
            <div style="font-size: 32px; font-weight: bold; margin-top: 10px; color: {change_color};">{net_change:+,}</div>
        </div>
    </div>
    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin: 20px 0;">
        <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 4px solid #d62728;">
            <div style="font-size: 14px; color: #6c757d; margin-bottom: 10px;">Dropped Members</div>
            <div style="font-size: 28px; font-weight: bold; color: #d62728;">{dropped:,}</div>
            <div style="font-size: 12px; color: #6c757d; margin-top: 5px;">{dropped_per:.2f}% of prior period</div>
        </div>
        <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 4px solid #2ca02c;">
            <div style="font-size: 14px; color: #6c757d; margin-bottom: 10px;">New Members</div>
            <div style="font-size: 28px; font-weight: bold; color: #2ca02c;">{new_members:,}</div>
            <div style="font-size: 12px; color: #6c757d; margin-top: 5px;">{new_per:.2f}% of prior period</div>
        </div>
    </div>
    """
    return html

def chat_with_agent(message, history):
    """Handle chat interaction with agent"""
    try:
        # Get response from orchestrator
        response = agent.run(message)
        
        if not isinstance(response, dict):
            # Return history with error message in dict format
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": "Error: Invalid response format"})
            return history, {}, {}
        
        data = response.get('data', {})
        signals = response.get('signals', {})
        text = response.get('text', '')
        org_cd = response.get('org_cd', '')
        
        # Check if user asked about drop but membership increased
        user_query_lower = message.lower()
        net_change = signals.get('net_change', 0)
        has_increase = net_change > 0
        
        # Build response as Markdown (Gradio Chatbot renders markdown better than HTML)
        warning_md = ""
        if "drop" in user_query_lower and has_increase:
            new_per = signals.get('new_per', 0)
            warning_md = f"⚠️ **Important:** Membership has **not dropped**. In fact, membership has **increased by {net_change:,} members** ({new_per:.2f}% growth).\n\n"
        
        # Only include the analysis text in the chatbot response
        # Metrics are displayed in the right section via charts
        response_md = f"""## 📊 Analysis for {org_cd}

{warning_md}{text}
"""
        
        # Append to history in Gradio 6.0 format: dict with 'role' and 'content'
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": response_md})
        
        return history, data, signals
        
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": error_msg})
        return history, {}, {}

def get_charts(data, signals):
    """Get chart components"""
    membership_chart = create_membership_chart(data, signals)
    movement_chart = create_movement_chart(signals)
    return membership_chart, movement_chart

def update_charts(data, signals):
    """Update charts based on response"""
    if not data or not signals:
        return None, None
    return create_membership_chart(data, signals), create_movement_chart(signals)

# Custom CSS for better styling
css = """
.gradio-container {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}
.chat-message {
    padding: 10px;
    border-radius: 8px;
}
"""

# Create Gradio interface
with gr.Blocks() as demo:
    gr.Markdown("""
    # 📊 Membership Impact Analytical Dashboard
    ### Ask questions about membership changes for any organization
    """)
    
    with gr.Row():
        with gr.Column(scale=2):
            chatbot = gr.Chatbot(
                label="Q&A Chat",
                height=600,
                show_label=True,
                container=True,
                sanitize_html=False,
                render_markdown=True
            )
            
            with gr.Row():
                msg = gr.Textbox(
                    label="Ask a question",
                    placeholder="For S5660_P801 why there is membership drop?",
                    scale=4,
                    container=False
                )
                submit_btn = gr.Button("Send", variant="primary", scale=1)
            
            with gr.Accordion("💡 Sample Questions", open=False):
                sample_questions = [
                    "For S5660_P801 why there is membership drop?",
                    "What caused the drop in H5522_P802?",
                    "Explain membership changes for H5522_P803",
                    "Why did S8841_P803 lose members?",
                    "Membership drop reasons for H2001_P816"
                ]
                gr.Examples(
                    examples=sample_questions,
                    inputs=msg
                )
        
        with gr.Column(scale=1):
            gr.Markdown("### 📈 Analytics")
            
            metrics_display = gr.Markdown(
                label="Key Metrics",
                value="*Metrics will appear here after you ask a question*"
            )
            
            membership_chart = gr.Plot(
                label="Membership Overview",
                show_label=True
            )
            
            movement_chart = gr.Plot(
                label="Member Movement",
                show_label=True
            )
    
    # Store data and signals as hidden components
    data_store = gr.State(value={})
    signals_store = gr.State(value={})
    
    # Event handlers
    def chat_fn(message, history):
        new_history, data, signals = chat_with_agent(message, history)
        chart1, chart2 = update_charts(data, signals)
        metrics_html = format_metrics(data, signals) if data and signals else "*No data available*"
        return new_history, data, signals, metrics_html, chart1, chart2
    
    submit_btn.click(
        fn=chat_fn,
        inputs=[msg, chatbot],
        outputs=[chatbot, data_store, signals_store, metrics_display, membership_chart, movement_chart]
    ).then(lambda: "", None, msg)
    
    msg.submit(
        fn=chat_fn,
        inputs=[msg, chatbot],
        outputs=[chatbot, data_store, signals_store, metrics_display, membership_chart, movement_chart]
    ).then(lambda: "", None, msg)
    
    gr.Markdown("""
    ---
    ### ℹ️ About
    This analytical dashboard provides insights into membership changes using:
    - **BigQuery** for real-time data queries
    - **PDF RAG** for contextual rulebook information
    - **LLM** for analytical responses
    """)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False, css=css, theme=gr.themes.Soft())
