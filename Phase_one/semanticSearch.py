from Phase_one.embeddings import embed
import numpy as np

#text = "What is the capital of France?"
#
#vector = embed(text).data[0].embedding
#print("*"*30,"EMBEDDING VECTOR","*"*30)
#print(len(vector))
#
#text2 = 'Berlin is the capital of Germany.'
#vector2 = embed(text2).data[0].embedding
#print("*"*30,"EMBEDDING VECTOR","*"*30) 
#print(len(vector2))
#
#text3 = 'Paris is the capital of France.'
#vector3 = embed(text3).data[0].embedding    
#print("*"*30,"EMBEDDING VECTOR","*"*30)
#print(len(vector3))

def cosine_similarity(vec1, vec2):
    dot_product = np.dot(vec1, vec2)
    norm_vec1 = np.linalg.norm(vec1)
    norm_vec2 = np.linalg.norm(vec2)
    
    if norm_vec1 == 0 or norm_vec2 == 0:
        return 0.0
    
    return dot_product / (norm_vec1 * norm_vec2)

#similarity1 = cosine_similarity(vector, vector2)
#similarity2 = cosine_similarity(vector, vector3)
#
#print(f"Cosine Similarity between '{text}' and '{text2}': {similarity1}")
#print(f"Cosine Similarity between '{text}' and '{text3}': {similarity2}")
#
def euclidean_distance(vec1, vec2):
    return np.linalg.norm(np.array(vec1) - np.array(vec2))

#distance1 = euclidean_distance(vector, vector2)
#distance2 = euclidean_distance(vector, vector3)
#print(f"Euclidean Distance between '{text}' and '{text2}': {distance1}")
#print(f"Euclidean Distance between '{text}' and '{text3}': {distance2}")

def dot_product(vec1, vec2):
    return np.dot(vec1, vec2)
#dot_product1 = dot_product(vector, vector2)
#dot_product2 = dot_product(vector, vector3)
#print(f"Dot Product between '{text}' and '{text2}': {dot_product1}")
#print(f"Dot Product between '{text}' and '{text3}': {dot_product2}")
