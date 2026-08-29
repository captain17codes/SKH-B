def knapsack_allocate(tickets, daily_budget, daily_workforce):
    """
    Solves the 0/1 Multi-dimensional Knapsack Problem.
    tickets: list of dicts. Required keys: 'id', 'budget_cost', 'workforce_hours', 'topsis_score'
    daily_budget: float/int
    daily_workforce: float/int
    
    Returns: (allocated_ticket_ids, max_score)
    """
    # Using a reachability DP approach (sparse DP) since capacities might be large or non-integers.
    # dp maps (current_budget, current_workforce) to (max_topsis_score, list_of_ticket_ids)
    dp = {(0.0, 0.0): (0.0, [])}
    
    for ticket in tickets:
        cost = float(ticket.get('budget_cost', 0))
        hours = float(ticket.get('workforce_hours', 0))
        score = float(ticket.get('topsis_score', 0))
        ticket_id = ticket['id']
        
        # Create a new dp dictionary for the current item to avoid modifying during iteration
        new_dp = dp.copy()
        
        for (b, w), (current_score, items) in dp.items():
            new_b = b + cost
            new_w = w + hours
            
            # Check constraints
            if new_b <= daily_budget and new_w <= daily_workforce:
                new_score = current_score + score
                
                # If this new state is better than an existing state, or it's a new state
                # Wait, for exact float matching it might create many states.
                # To prevent state explosion, we can round to 2 decimal places if needed, 
                # but for small datasets (N<100) this sparse DP is usually fine.
                # Let's round the keys to 4 decimal places to avoid floating point issues.
                state_key = (round(new_b, 4), round(new_w, 4))
                
                if state_key not in new_dp or new_dp[state_key][0] < new_score:
                    new_dp[state_key] = (new_score, items + [ticket_id])
                    
        # To optimize, we could prune dominated states (same or higher cost/hours but lower score),
        # but for our use case (small number of tickets per day), it's not strictly necessary.
        dp = new_dp
        
    # Find the maximum score among all valid combinations
    best_score = -1.0
    best_combination = []
    
    for (b, w), (score, items) in dp.items():
        if score > best_score:
            best_score = score
            best_combination = items
            
    return best_combination, best_score
