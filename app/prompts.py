SYSTEM_PROMPT = """
You are an expert data analyst specializing in membership impact analysis. Your role is to provide deep analytical reasoning and clear explanations.

**Your Analytical Approach:**
1. **Observe** - Start by clearly stating what the data shows (the facts)
2. **Analyze** - Examine patterns, relationships, and signals in the data
3. **Reason** - Connect the dots: explain WHY things happened based on the signals and patterns
4. **Explain** - Provide clear, logical explanations that help the user understand not just WHAT happened, but WHY it happened
5. **Contextualize** - Reference the rulebook framework to provide deeper insights when relevant

**Reasoning Guidelines:**
- Think step-by-step: What does the data show? What patterns emerge? What explains these patterns?
- Use causal reasoning: Connect data signals to likely causes (e.g., "The combination of network ID mapping changes and membership movement suggests re-attribution of members")
- Explain relationships: Show how different data points relate to each other (e.g., "While X members dropped, Y new members were added, resulting in a net change of Z")
- Provide insights: Go beyond stating facts - explain what they mean and why they matter
- Use specific numbers: Reference exact counts and percentages to support your reasoning
- Reference signals: Explain how analytical signals (movement, retroactive terminations, config changes) inform your understanding

**Writing Style:**
- Write in a clear, analytical, conversational style
- Flow naturally - don't use templates or structured sections
- Be CONCISE and direct - keep responses brief (2-3 short paragraphs maximum)
- Focus on the key findings and main reasoning - avoid unnecessary elaboration
- Make it accessible - explain technical concepts in understandable terms

DO NOT use formal templates, structured formats, or sections like "Summary:", "Likely reasons:", "Evidence used:", "Confidence:". Just provide natural analytical reasoning with clear explanations.
"""

def build_response_prompt(membership_data, signals, rules_text, provider_changes_count, query):
    """Build an analytical prompt for the LLM."""
    
    prior = membership_data.get('prior_members', 0)
    current = membership_data.get('current_members', 0)
    dropped_cnt = signals.get('dropped_mbr_cnt', 0)
    dropped_per = signals.get('dropped_per', 0)
    new_cnt = signals.get('new_mbr_cnt', 0)
    new_per = signals.get('new_per', 0)
    net_change = signals.get('net_change', 0)
    has_drop = dropped_cnt > 0 and net_change < 0
    has_increase = net_change > 0
    org_cd = membership_data.get('org_cd', 'UNKNOWN')
    retro_term = membership_data.get('retro_term_mem_count', 0)
    
    # Build analytical insights
    insights = []
    
    # Primary observation
    if has_increase and dropped_cnt == 0:
        insights.append(f"KEY FINDING: Membership increased by {net_change:,} members ({new_per:.2f}% growth). Zero members dropped.")
    elif has_drop:
        insights.append(f"KEY FINDING: Membership decreased by {abs(net_change):,} members ({dropped_per:.2f}% drop).")
    elif has_increase:
        insights.append(f"KEY FINDING: Membership increased by {net_change:,} members ({new_per:.2f}% growth), despite {dropped_cnt:,} members dropping.")
    
    # Analytical observations
    if signals.get('movement'):
        insights.append("ANALYTICAL SIGNAL: Membership movement detected - members were reassigned between organizations (moved_to/moved_from indicators present).")
    
    if signals.get('retro_dominant') and dropped_cnt > 0:
        retro_pct = (retro_term / dropped_cnt * 100) if dropped_cnt > 0 else 0
        insights.append(f"ANALYTICAL SIGNAL: Retroactive terminations ({retro_term:,} members, {retro_pct:.1f}% of drops) suggest data corrections or backdated terminations.")
    
    config_changes = []
    if signals.get('has_network_id'):
        config_changes.append("network ID mapping")
    if signals.get('has_plan_carrier_id'):
        config_changes.append("plan carrier ID mapping")
    if signals.get('has_file_id'):
        config_changes.append("file ID mapping")
    if signals.get('has_termed_key'):
        config_changes.append("termed key configuration")
    
    if config_changes:
        insights.append(f"ANALYTICAL SIGNAL: Provider configuration changes detected: {', '.join(config_changes)}. These mapping changes can re-attribute membership between organizations.")
    
    if signals.get('churn'):
        insights.append("ANALYTICAL PATTERN: High churn pattern detected - significant drops offset by significant additions, suggesting reclassification or member movement.")
    
    # User's question context
    user_asked_about_drop = any(word in query.lower() for word in ["drop", "lose", "decreas", "down", "fell", "decline"])
    
    prompt = f"""Question: "{query}"

You're analyzing membership data for {org_cd}. Here's what the data shows:

**Membership Metrics:**
- Prior period (Nov 2025): {prior:,} members
- Current period (Dec 2025): {current:,} members  
- Net change: {net_change:+,} members ({((net_change/prior)*100):+.2f}% change)

**Member Movement:**
- Dropped: {dropped_cnt:,} members ({dropped_per:.2f}% of prior period)
- New: {new_cnt:,} members ({new_per:.2f}% of prior period)
- Retroactive terminations: {retro_term:,} members

**Analytical Signals:**
{chr(10).join(f"- {insight}" for insight in insights)}

**Provider Configuration Changes:** {provider_changes_count} change(s) detected

**Relevant Analysis Framework (from rulebook):**
{rules_text[:2000] if rules_text else "No specific rules retrieved"}

**Your Task - Provide Analytical Reasoning:**

Answer the user's question by following this reasoning structure:

1. **State the facts** - Directly address their question and clearly state what the data shows
   - If they asked about a "drop" but membership increased, start by correcting this directly
   - State the key numbers: net change, prior vs current, dropped vs new members

2. **Explain the patterns** - Walk through what the numbers reveal
   - What does the movement (drops vs adds) tell you?
   - What patterns do you see in the data?

3. **Reason about the causes** - Explain WHY this happened based on the analytical signals
   - Connect the signals (movement, retroactive terminations, config changes) to likely causes
   - Explain how these signals relate to each other and to the membership change
   - Reference the rulebook framework to provide deeper context when relevant
   - Use causal reasoning: "Because [signal X], this likely means [explanation Y]"

4. **Provide insights** - What does this mean and why does it matter?
   - What are the implications of these patterns?
   - What insights can be drawn from this analysis?

5. **Be specific** - Use exact numbers, percentages, and signal details throughout your reasoning

IMPORTANT: Write exactly 4 paragraphs, each 2-3 lines long. Structure your response as follows:

Paragraph 1: Answer the question directly and state the key finding (what happened - increase/drop and by how much). 2-3 lines.

Paragraph 2: Explain the main cause/reason based on the data signals (connect the most relevant signals to what likely caused it). 2-3 lines.

Paragraph 3: Provide reasoning from the rulebook framework - reference the relevant rules/patterns from the rulebook context provided above that explain what's happening. 2-3 lines.

Paragraph 4: Conclude with the key insight or what this means for the organization. 2-3 lines.

Keep each paragraph concise (2-3 lines each, total ~100-120 words). Make sure Paragraph 3 specifically references the rulebook context provided.

"""
    
    if user_asked_about_drop and has_increase:
        prompt += """
IMPORTANT CORRECTION: The user asked about a membership drop, but the data shows membership INCREASED. 
Start your answer by directly and clearly correcting this: "Actually, membership didn't drop - it increased by [X] members ([Y]% growth)."
Then provide your analytical reasoning:
- Explain what the data actually shows (net increase)
- Analyze what drove the increase (new members, movement patterns, etc.)
- Reason through why this might have happened based on the signals
- Explain the discrepancy between the user's expectation and the actual data
"""
    
    # Add reasoning prompt enhancement
    prompt += """
Remember: Write exactly 4 paragraphs (each 2-3 lines). Paragraph 3 MUST reference the rulebook framework provided above. Keep it concise (~100-120 words total).
"""
    
    return prompt
