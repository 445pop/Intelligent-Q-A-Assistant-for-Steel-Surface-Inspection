def is_overlapping(box1, box2):
    """
    Check if two bounding boxes overlap.

    Parameters:
        box1 (dict): Dictionary representing the first bounding box with keys 'x', 'y', 'w', 'h'.
        box2 (dict): Dictionary representing the second bounding box with keys 'x', 'y', 'w', 'h'.

    Returns:
        bool: True if the boxes overlap, False otherwise.
    """
    x1, y1, w1, h1 = box1['x'], box1['y'], box1['w'], box1['h']
    x2, y2, w2, h2 = box2['x'], box2['y'], box2['w'], box2['h']

    if (x1 < x2 + w2 and x1 + w1 > x2 and
            y1 < y2 + h2 and y1 + h1 > y2):
        return True
    return False


def remove_overlapping_boxes(merged_boxes_list, cluster_list):
    """
    Remove overlapping boxes based on confidence scores.

    Parameters:
        merged_boxes_list (list): List containing lists of bounding boxes for each class.
        cluster_list (list): List containing clusters for each class.

    Returns:
        tuple: Updated merged_boxes_list and cluster_list after removing overlapping boxes.
    """
    to_delete_indices = set()  # Set to store indices of boxes to delete

    # Iterate through each class
    for i in range(len(merged_boxes_list) - 1):
        for j in range(i + 1, len(merged_boxes_list)):
            # Iterate through boxes in class i
            for k1, box1 in enumerate(merged_boxes_list[i]):
                # Iterate through boxes in class j
                for k2, box2 in enumerate(merged_boxes_list[j]):
                    if is_overlapping(box1, box2):
                        # Determine which box to delete based on confidence score
                        if box1['conf'] < box2['conf']:
                            to_delete_indices.add((i, k1))
                        else:
                            to_delete_indices.add((j, k2))
    # Delete boxes and corresponding clusters
    for idx in sorted(to_delete_indices, reverse=True):
        del merged_boxes_list[idx[0]][idx[1]]
        del cluster_list[idx[0]][idx[1]]

    return merged_boxes_list, cluster_list


# Example usage:
merged_boxes_list = [
    [{'x': 50, 'y': 50, 'w': 50, 'h': 50, 'conf': 0.9},
     {'x': 150, 'y': 150, 'w': 50, 'h': 50, 'conf': 0.8},
     {'x': 70, 'y': 70, 'w': 50, 'h': 50, 'conf': 0.7}],
    [{'x': 70, 'y': 70, 'w': 50, 'h': 50, 'conf': 0.6},
     {'x': 180, 'y': 180, 'w': 50, 'h': 50, 'conf': 0.8}],
    [{'x': 200, 'y': 200, 'w': 50, 'h': 50, 'conf': 0.95},
     {'x': 250, 'y': 250, 'w': 50, 'h': 50, 'conf': 0.85},
     {'x': 270, 'y': 270, 'w': 50, 'h': 50, 'conf': 0.75}],
]

cluster_list = [
    [5, 6, 7],
    [3, 4],
    [0, 1, 2],

    # More lists...
]

merged_boxes_list, cluster_list = remove_overlapping_boxes(merged_boxes_list, cluster_list)
print(merged_boxes_list)
print(cluster_list)
