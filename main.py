import os
from dotenv import load_dotenv
from CrewAI.crew import SqlCrew

# Load environment variables (API Keys)
load_dotenv()

def run_sql_crew():
    print("\n" + "="*50)
    print("KICKING OFF THE HYBRID SQL CREW (Project Structure)...")
    print("="*50 + "\n")
    
    inputs = {
        'topic': 'Am I over-budget? If yes, identify the top 3 merchants draining my money and tell me exactly how much to cut from each.'
    }
    
    # Initialize the crew from the automated structure
    result = SqlCrew().crew().kickoff(inputs=inputs)
    
    print("\n" + "="*50)
    print("FINAL REPORT GENERATED:")
    print("="*50 + "\n")
    print(result)

    # Save to file with error handling
    report_file = "report.md"
    try:
        with open(report_file, "w", encoding='utf-8') as f:
            f.write(str(result))
        print(f"\n[INFO] Report saved to {os.path.abspath(report_file)}")
    except PermissionError:
        print(f"\n[WARNING] Could not save report to '{report_file}': Permission denied.")
        print("[INFO] Report is displayed above but could not be written to disk.")
    except OSError as e:
        print(f"\n[WARNING] Could not save report to '{report_file}': {str(e)}")
        print("[INFO] Report is displayed above but could not be written to disk.")

if __name__ == "__main__":
    run_sql_crew()
