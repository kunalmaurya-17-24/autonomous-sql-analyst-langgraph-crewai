from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from CrewAI.sql_tools import LangGraphSQLTool

@CrewBase
class SqlCrew():
	"""SqlCrew crew"""

	agents_config = 'config/agents.yaml'
	tasks_config = 'config/tasks.yaml'

	def __init__(self):
		# Use string model name for CrewAI compatibility
		# CrewAI will automatically configure the LLM using GOOGLE_API_KEY from .env
		pass

	@agent
	def data_analyst(self) -> Agent:
		return Agent(
			config=self.agents_config['data_analyst'],
			tools=[LangGraphSQLTool()],
			llm="gemini/gemini-2.5-flash",  # Best for development: ~1000 requests/day
			verbose=True
		)

	@agent
	def technical_writer(self) -> Agent:
		return Agent(
			config=self.agents_config['technical_writer'],
			llm="gemini/gemini-2.5-flash",  # Best for development: ~1000 requests/day
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
