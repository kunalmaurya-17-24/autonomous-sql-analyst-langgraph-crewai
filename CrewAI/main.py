#!/usr/bin/env python
import sys
import os
from CrewAI.crew import SqlCrew

# This main.py is for running the crew directly from the CrewAI folder
def run():
    """
    Run the crew.
    """
    inputs = {
        'topic': 'Show me the top 5 product categories by revenue in São Paulo'
    }
    SqlCrew().crew().kickoff(inputs=inputs)

def train():
    """
    Train the crew for a given number of iterations.
    """
    inputs = {
        'topic': 'Show me the top 5 product categories by revenue in São Paulo'
    }
    try:
        SqlCrew().crew().train(n_iterations=int(sys.argv[1]), filename=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while training the crew: {e}")

def replay():
    """
    Replay the crew execution from a specific task.
    """
    try:
        SqlCrew().crew().replay(task_id=sys.argv[1])

    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")

def test():
    """
    Test the crew execution and returns the expected output.
    """
    inputs = {
        'topic': 'Show me the top 5 product categories by revenue in São Paulo'
    }
    try:
        SqlCrew().crew().test(n_iterations=int(sys.argv[1]), openai_model_name=sys.argv[2], inputs=inputs)

    except Exception as e:
        raise Exception(f"An error occurred while replaying the crew: {e}")

if __name__ == "__main__":
    run()
