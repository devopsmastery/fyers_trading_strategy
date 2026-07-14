import os

def clean_file(filepath, exclude_set=None):
    if exclude_set is None:
        exclude_set = set()
    
    if not os.path.exists(filepath):
        return set()
        
    with open(filepath, 'r') as f:
        lines = f.readlines()
        
    unique_stocks = []
    seen = set()
    
    for line in lines:
        s = line.strip()
        # Ignore empty lines or comments
        if not s or s.startswith('#'):
            continue
            
        if s not in seen and s not in exclude_set:
            unique_stocks.append(s)
            seen.add(s)
            
    with open(filepath, 'w') as f:
        for s in unique_stocks:
            f.write(s + '\n')
            
    return seen

def main():
    print("========================================")
    print("      DEDUPLICATE STOCKS UTILITY")
    print("========================================")
    
    # 1. Clean stocks_to_test.txt
    main_set = clean_file('stocks_to_test.txt')
    print(f"Cleaned stocks_to_test.txt. It now has {len(main_set)} unique stocks.")
    
    # 2. Clean stocks_watchlist.txt, excluding any stocks already in main_set
    watch_set = clean_file('stocks_watchlist.txt', exclude_set=main_set)
    print(f"Cleaned stocks_watchlist.txt. It now has {len(watch_set)} unique stocks.")
    print("========================================")

if __name__ == "__main__":
    main()
