#!pip install orange3
import Orange
import matplotlib.pyplot as plt
from google.colab import files
import pandas as pd

def run_test():
    names = [
        'logit_comb_1',
        'logit_comb_2',
        'logit_comb_3',
        'logit_comb_4',
        'knn_50_comb_1',
        'knn_50_comb_2',
        'knn_50_comb_3',
        'lsvm_comb_1',
        'lsvm_comb_2',
        'lsvm_comb_3',
        'lsvm_comb_4',
        'svm_comb_1',
        'svm_comb_2',
        'svm_comb_3',
        'svm_comb_4',
        'nn_comb_1',
        'nn_comb_2',
        'nn_comb_3',
        'nn_comb_4',
        'nn_comb_5',
    ]

    avranks = [
        17.22222222222222,
        14.333333333333332,
        3.5000000000000004,
        5.222222222222221,
        16.77777777777778,
        13.222222222222223,
        5.888888888888888,
        14.722222222222221,
        11.000000000000002,
        1.888888888888889,
        5.0,
        15.88888888888889,
        13.666666666666668,
        7.888888888888888,
        12.833333333333334,
        15.555555555555557,
        14.277777777777777,
        6.9444444444444455,
        12.166666666666668,
        12.166666666666668
    ]
    
    pairs = zip(names, avranks)
    pairs = sorted(pairs, key=lambda x: x[1])
    for i in pairs:
        print(i)



    eos = len(names)
    print(len(names), len(avranks))
    cd = Orange.evaluation.compute_CD(avranks[0:eos], 90 , alpha = '0.05' , test = 'nemenyi' )#'bonferroni-dunn')# test='nemenyi') 
    print(cd)
    Orange.evaluation.graph_ranks(avranks[0:eos], names[0:eos], cd = cd, width = 12, textspace = 2.5)
    a = plt.show()
    #plt.savefig('labeled_ration_5%.png', format='png', dpi=600) 

run_test()
