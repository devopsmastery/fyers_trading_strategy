import os
import sys

# Ensure parent directory is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from live_trading.execute_trades import main

if __name__ == "__main__":
    print("========================================")
    print("        STARTING DAILY DRY RUN          ")
    print("========================================")
    # Force DRY_RUN mode for this execution
    os.environ["DRY_RUN"] = "True"
    
    # Run the main scanner
    main()
