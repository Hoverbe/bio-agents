from backend.src.agents.simple_agent import SimpleAgent

llm = SimpleAgent(name="测试Agent", llm=HelloAgentsLLM(), system_prompt="你是一个测试用的智能体。")
