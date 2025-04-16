import numpy as np

def get_embedding(file_path, start, increase):
    with open(file_path, 'r') as file:
        lines = file.readlines()

    embeddings = []

    for i in range(start, len(lines), increase):  
        embedding_str = lines[i].strip()
        embedding = eval(embedding_str)  
        embeddings.append(embedding)
    
    return np.array(embeddings)

def main():
    embeddings = get_embedding('./output/10ksample/10ksample.csv', 3, 5)
    attack_embedding = get_embedding('./output/attack/attack.csv', 2, 4)
    merged_embeddings = np.concatenate((embeddings, attack_embedding), axis=0)
    
    np.savetxt('./output/attack/merged_embeddings.csv', merged_embeddings, delimiter=',')

if __name__ == "__main__":
    main()