from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from stock_strategy_growth_crew.tools import (
    CompetitorSnapshotTool,
    LeadPipelineTool,
    TrendSignalTool,
    TrialActivityTool,
)

@CrewBase
class StockStrategyGrowthCrew():
    """StockStrategyGrowthCrew crew"""

    agents: list[BaseAgent]
    tasks: list[Task]

    @agent
    def market_strategist(self) -> Agent:
        return Agent(
            config=self.agents_config['market_strategist'], # type: ignore[index]
            tools=[TrendSignalTool(), CompetitorSnapshotTool()],
            verbose=True
        )

    @agent
    def compliance_officer(self) -> Agent:
        return Agent(
            config=self.agents_config['compliance_officer'], # type: ignore[index]
            verbose=True
        )

    @agent
    def x_editor(self) -> Agent:
        return Agent(
            config=self.agents_config['x_editor'], # type: ignore[index]
            tools=[TrendSignalTool()],
            verbose=True
        )

    @agent
    def xiaohongshu_editor(self) -> Agent:
        return Agent(
            config=self.agents_config['xiaohongshu_editor'], # type: ignore[index]
            tools=[TrendSignalTool()],
            verbose=True
        )

    @agent
    def wechat_editor(self) -> Agent:
        return Agent(
            config=self.agents_config['wechat_editor'], # type: ignore[index]
            tools=[TrendSignalTool()],
            verbose=True
        )

    @agent
    def xueqiu_editor(self) -> Agent:
        return Agent(
            config=self.agents_config['xueqiu_editor'], # type: ignore[index]
            tools=[TrendSignalTool()],
            verbose=True
        )

    @agent
    def ops_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['ops_analyst'], # type: ignore[index]
            tools=[TrendSignalTool(), CompetitorSnapshotTool(), LeadPipelineTool(), TrialActivityTool()],
            verbose=True
        )

    @agent
    def lead_manager(self) -> Agent:
        return Agent(
            config=self.agents_config['lead_manager'], # type: ignore[index]
            tools=[LeadPipelineTool()],
            verbose=True
        )

    @agent
    def trial_success_manager(self) -> Agent:
        return Agent(
            config=self.agents_config['trial_success_manager'], # type: ignore[index]
            tools=[TrialActivityTool()],
            verbose=True
        )

    @agent
    def sales_manager(self) -> Agent:
        return Agent(
            config=self.agents_config['sales_manager'], # type: ignore[index]
            tools=[LeadPipelineTool(), TrialActivityTool()],
            verbose=True
        )

    @task
    def growth_strategy_task(self) -> Task:
        return Task(
            config=self.tasks_config['growth_strategy_task'], # type: ignore[index]
        )

    @task
    def compliance_review_task(self) -> Task:
        return Task(
            config=self.tasks_config['compliance_review_task'], # type: ignore[index]
        )

    @task
    def x_post_task(self) -> Task:
        return Task(
            config=self.tasks_config['x_post_task'], # type: ignore[index]
        )

    @task
    def xiaohongshu_post_task(self) -> Task:
        return Task(
            config=self.tasks_config['xiaohongshu_post_task'], # type: ignore[index]
        )

    @task
    def wechat_post_task(self) -> Task:
        return Task(
            config=self.tasks_config['wechat_post_task'], # type: ignore[index]
        )

    @task
    def xueqiu_post_task(self) -> Task:
        return Task(
            config=self.tasks_config['xueqiu_post_task'], # type: ignore[index]
        )

    @task
    def ops_summary_task(self) -> Task:
        return Task(
            config=self.tasks_config['ops_summary_task'], # type: ignore[index]
            output_file='growth_execution_plan.md'
        )

    @task
    def lead_triage_task(self) -> Task:
        return Task(
            config=self.tasks_config['lead_triage_task'], # type: ignore[index]
            output_file='lead_triage.md'
        )

    @task
    def trial_success_task(self) -> Task:
        return Task(
            config=self.tasks_config['trial_success_task'], # type: ignore[index]
            output_file='trial_followup_plan.md'
        )

    @task
    def sales_conversion_task(self) -> Task:
        return Task(
            config=self.tasks_config['sales_conversion_task'], # type: ignore[index]
            output_file='sales_conversion_plan.md'
        )

    @task
    def crm_dashboard_task(self) -> Task:
        return Task(
            config=self.tasks_config['crm_dashboard_task'], # type: ignore[index]
            output_file='crm_dashboard.md'
        )

    @crew
    def crew(self) -> Crew:
        """Creates the StockStrategyGrowthCrew crew"""
        return Crew(
            agents=self.agents, # Automatically created by the @agent decorator
            tasks=self.tasks, # Automatically created by the @task decorator
            process=Process.sequential,
            verbose=True,
        )
