from crewai import Agent, Crew, Process, Task, LLM
from crewai.project import CrewBase, agent, crew, task
from CrewAI.sql_tools import LangGraphSQLTool
import opik
from opik.integrations.langchain import OpikTracer
opik_tracer = OpikTracer()

@CrewBase
class SqlCrew():
	"""SqlCrew crew"""

	agents_config = 'config/agents.yaml'
	tasks_config = 'config/tasks.yaml'

	def __init__(self):
		# Validate config files exist before initializing
		import os
		agents_path = os.path.join(os.path.dirname(__file__), self.agents_config)
		tasks_path = os.path.join(os.path.dirname(__file__), self.tasks_config)
		
		if not os.path.exists(agents_path):
			raise FileNotFoundError(
				f"CRITICAL: Agents config not found at '{agents_path}'.\n"
				f"Please ensure 'config/agents.yaml' exists in the CrewAI directory."
			)
		
		if not os.path.exists(tasks_path):
			raise FileNotFoundError(
				f"CRITICAL: Tasks config not found at '{tasks_path}'.\n"
				f"Please ensure 'config/tasks.yaml' exists in the CrewAI directory."
			)
		
		# Initialize the LLM using CrewAI's native wrapper (LiteLLM)
		# This avoids the "models/gemini..." prefix issue from langchain_google_genai
		self.llm = LLM(
			model="gemini/gemini-2.5-flash", 
			temperature=0,
			callbacks=[opik_tracer]
		)

	@agent
	def data_analyst(self) -> Agent:
		return Agent(
			config=self.agents_config['data_analyst'],
			tools=[LangGraphSQLTool()],
			llm=self.llm,
			verbose=True
		)

	@agent
	def technical_writer(self) -> Agent:
		return Agent(
			config=self.agents_config['technical_writer'],
			llm=self.llm,
			verbose=True
		)

	@task
	def analysis_task(self) -> Task:
		return Task(
			config=self.tasks_config['analysis_task'],
		)

	@task
	def reporting_task(self) -> Task:
		return Task(
			config=self.tasks_config['reporting_task'],
		)

	@crew
	def crew(self) -> Crew:
		"""Creates the SqlCrew crew"""
		return Crew(
			agents=self.agents,
			tasks=self.tasks,
			process=Process.sequential,
			verbose=True,
		)
