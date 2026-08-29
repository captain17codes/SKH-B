import numpy as np

def distance_tfn(tfn1, tfn2):
    """Calculate the distance between two Triangular Fuzzy Numbers using the vertex method."""
    l1, m1, u1 = tfn1
    l2, m2, u2 = tfn2
    return np.sqrt((1.0 / 3.0) * ((l1 - l2)**2 + (m1 - m2)**2 + (u1 - u2)**2))

def normalize_fuzzy_matrix(matrix, criteria_types):
    """
    Normalize the fuzzy decision matrix.
    matrix: list of lists of TFNs (tuples or lists of 3 floats)
            shape: (num_alternatives, num_criteria, 3)
    criteria_types: list of strings, either 'benefit' or 'cost'
    """
    matrix = np.array(matrix)
    num_alternatives, num_criteria, _ = matrix.shape
    normalized_matrix = np.zeros_like(matrix, dtype=float)

    for j in range(num_criteria):
        if criteria_types[j] == 'benefit':
            c_max = np.max(matrix[:, j, 2]) # max of upper bounds
            for i in range(num_alternatives):
                l, m, u = matrix[i, j]
                normalized_matrix[i, j] = [l / c_max, m / c_max, u / c_max] if c_max > 0 else [0, 0, 0]
        elif criteria_types[j] == 'cost':
            a_min = np.min(matrix[:, j, 0]) # min of lower bounds
            for i in range(num_alternatives):
                l, m, u = matrix[i, j]
                # To avoid division by zero:
                norm_l = a_min / u if u > 0 else 0
                norm_m = a_min / m if m > 0 else 0
                norm_u = a_min / l if l > 0 else 0
                normalized_matrix[i, j] = [norm_l, norm_m, norm_u]

    return normalized_matrix

def apply_weights(normalized_matrix, weights):
    """
    Apply TFN weights to the normalized matrix.
    weights: list of TFNs for each criterion
    """
    num_alternatives, num_criteria, _ = normalized_matrix.shape
    weighted_matrix = np.zeros_like(normalized_matrix)

    for i in range(num_alternatives):
        for j in range(num_criteria):
            w_l, w_m, w_u = weights[j]
            x_l, x_m, x_u = normalized_matrix[i, j]
            weighted_matrix[i, j] = [x_l * w_l, x_m * w_m, x_u * w_u]

    return weighted_matrix

def calculate_ideal_solutions(num_criteria):
    """
    Computes FPIS (A*) and FNIS (A-). 
    As per standard normalized fuzzy space: 
    v_j* = (1, 1, 1) and v_j- = (0, 0, 0)
    """
    fpis = np.array([[1.0, 1.0, 1.0]] * num_criteria)
    fnis = np.array([[0.0, 0.0, 0.0]] * num_criteria)
    return fpis, fnis

def calculate_closeness_coefficient(weighted_matrix, fpis, fnis):
    """
    Calculate the relative closeness coefficient for each alternative.
    """
    num_alternatives, num_criteria, _ = weighted_matrix.shape
    closeness_scores = np.zeros(num_alternatives)

    for i in range(num_alternatives):
        d_star = 0
        d_minus = 0
        for j in range(num_criteria):
            d_star += distance_tfn(weighted_matrix[i, j], fpis[j])
            d_minus += distance_tfn(weighted_matrix[i, j], fnis[j])
        
        if d_star + d_minus == 0:
            closeness_scores[i] = 0
        else:
            closeness_scores[i] = d_minus / (d_star + d_minus)

    return closeness_scores

def run_prioritization(tickets_data, criteria_config):
    """
    Main entry point.
    tickets_data: list of dicts, e.g., 
      [{'id': 1, 'scores': [[l,m,u], [l,m,u], ...]}, ...]
    criteria_config: dict, e.g.,
      {'types': ['benefit', 'benefit', 'benefit', 'cost'],
       'weights': [[w_l,w_m,w_u], ...]}
    
    Returns: list of dicts with topsis_score appended, sorted descending
    """
    if not tickets_data:
        return []

    matrix = [t['scores'] for t in tickets_data]
    criteria_types = criteria_config['types']
    weights = criteria_config['weights']

    normalized = normalize_fuzzy_matrix(matrix, criteria_types)
    weighted = apply_weights(normalized, weights)
    fpis, fnis = calculate_ideal_solutions(len(criteria_types))
    scores = calculate_closeness_coefficient(weighted, fpis, fnis)

    results = []
    for i, ticket in enumerate(tickets_data):
        t = ticket.copy()
        t['topsis_score'] = scores[i]
        results.append(t)
        
    # Sort descending by topsis_score
    results.sort(key=lambda x: x['topsis_score'], reverse=True)
    return results
