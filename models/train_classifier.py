# basic imports
import json
import re
import time
import numpy as np
import pandas as pd
from pandas.api.types import CategoricalDtype
from matplotlib import pyplot as plt
import random

# import to load the data from a SQLite database
import sqlalchemy as db
from sqlalchemy import create_engine

# imports of custom transformers
import sys
sys.path.insert(1, './')
from transformers.my_transformers import *

# import to save the trained model into a file
import pickle




labels = []

def load_data(database_filepath):
    '''
    USAGE 
           load the data that we'll use to train the model
    INPUT
           database_filepath: database with the messages to train the model       
    OUTPUT
           X: df with the columns with the featrues
           Y: df with the columns with the response  
           labels: list with names of the labels           
    '''
    engine = db.create_engine('sqlite:///' + database_filepath)
    df = pd.read_sql_table('messages', engine)
    X = df[['message', 'genre', 'len']]
    Y = df.drop(columns = ['id', 'message', 'original', 'genre', 'len', 'lang']).values
    labels = df.columns[4:-2]
    return X, Y, labels




def model_pipeline_rf_complete():
    '''
       define a pipeline for random forest with the features:
       tfidf: ftidf features of the column message.
       person: message makes refference to a person?
       organization: message makes refference to an organization?
       gpe: message makes refference to a geopolitical entity?
       len: longitude of the message
       genre: categorical variable: news, direct or social.
    '''
    pipeline = Pipeline([
        ('features', FeatureUnion(
             transformer_list=[
                 # tfidf features over column message
                 ('text_pipeline', Pipeline([
                     ("selector", ColumnSelector(column="message")),
                     ('vect', CountVectorizer(tokenizer=Tokenizer.tokenize, max_features = 5000)),
                     ('tfidf', TfidfTransformer())
                     ])
                  ),
                 # search words features over columns message
                  ('word_pipeline', Pipeline([
                        ("selector", ColumnSelector(column="message")),
                         ('word_features', FeatureUnion([
                             ('person', PersonExtractor()),
                             ('organization', OrganizationExtractor()),
                             ('gpe', GPEExtractor())
                             ])
                         )
             
                   ])),
                 # len features. OneHotEncoding of column genre
                   ('len_pipeline', Pipeline([
                       ('selector', ColumnSelector(column="len")),
                       ('reshape', Reshape_Array()),
                       ('len', StandardScaler())
                       ])
                   ),
                 # genre features. OneHotEncoding of column genre
                   ('genre_pipeline', Pipeline([
                       ('selector', ColumnSelector(column="genre")),
                       ('reshape', Reshape_Array()),
                       ('genre', OneHotEncoder())
                       ])
                   )
            ]
        )),
        # apply Random Forests method
        ('multi_clf', MultiOutputClassifier(RandomForestClassifier(n_estimators=35, min_samples_split = 3)))
    ])
    return pipeline


def model_pipeline_svc_gs():
    '''
       Define a LinearSVC pipeline
    '''    
    pipeline = Pipeline([
        ('vect', CountVectorizer(tokenizer=Tokenizer.tokenize, max_features = None)),
        ('tfidf', TfidfTransformer()),
        ('multi_clf', MultiOutputClassifier(LinearSVC(C=1)))
    ])
    return pipeline
    


def model_pipeline_rf_gs():
    '''
       Define a Random Forests pipeline
    '''
    pipeline = Pipeline([
        ('vect', CountVectorizer(tokenizer=Tokenizer.tokenize, max_features = 5000)),
        ('tfidf', TfidfTransformer()),
        ('multi_clf', MultiOutputClassifier(RandomForestClassifier(n_estimators=35, min_samples_split = 3)))
    ])
    return pipeline
    
    
def show_plot(df):
    '''
    USAGE:
        print different plots depending of the stat option
    INPUT:
        df: dataframe with the information of precision, recall, f1-scores, etc.
    '''
    # select when the label value is equal to 1 and prepare the dataframe to 
    # draw a plot.
    aux_results = df[df.value == 1].sort_values(by = 'recall', 
                                                ascending = False)
                                                
    aux_results = aux_results.set_index('label')
    
    # It draws a barplot with the results of the training
    aux_results.plot(kind= 'bar' ,
                     y = ['f1-score', 'recall', 'precision', 'support'],
                     secondary_y = 'support',
                     use_index = True,
                     rot= 90,
                     width = 0.8
                     )
    plt.show()


def display_results(y_test, y_pred, labels, printout = False):
    '''
    USAGE: 
        It prints the resulst of sklearn.metrics.classification_report.
        
    INPUT
        y_test: Lists with the real values for the response variables
        y_pred: Lists with the predicted values for the response variables.
        labels: Names or labels for the response variables
        printout: False: returns a dataframe with the sesult values for each label
                  True: returns a printout.
    OUTPUT
        result: A dataframe with the values of precision, reacall, f1-score, support,
                accuracy for each label and value (0 or 1)
    '''
    
    i= 0
    
    # we can decied if we want the result in a printout or in a dataframe
    if printout == False:
        data = []
        # we define an empty dataframe
        result = pd.DataFrame(columns = ['label', 'value', 'precision', 'recall', 'f1-score', 'support', 'accuracy'])
        for label in labels:
            # for each label we execute the function classification_report. 
            # We ask for the result as a dictionary
            class_report = classification_report(y_test[:,i], y_pred[:,i], output_dict = True)
            
            # prepare the information in a list to be saved into the result dataframe
            # for value of the label 0
            data = [label , 0, 
                    class_report['0']['precision'], 
                    class_report['0']['recall'],
                    class_report['0']['f1-score'],
                    class_report['0']['support'], 
                    class_report['accuracy']]
            # save the data into the result dataframe
            s = pd.Series(data, index=result.columns)
            result = result.append(s, ignore_index=True)
            
            # prepare the information in a list to be saved into the result dataframe
            # for value of the label 1
            data = [label , 1, 
                    class_report['1']['precision'], 
                    class_report['1']['recall'],
                    class_report['1']['f1-score'],
                    class_report['1']['support'], 
                    class_report['accuracy']]
            # save the data into the result dataframe
            s = pd.Series(data, index=result.columns)
            result = result.append(s, ignore_index=True)
            i += 1
        # return a dataframe with the data of precision, recall, etc for all the labels
        return result
        
    else:
        # if we want the result in a printout
        for label in labels:
            # for each label we execute the function classification_report. 
            # We ask for the result as a printout
            class_report = classification_report(y_test[:,i], y_pred[:,i])
            accuracy = (y_pred[:,i] == y_test[:,i]).mean()
            # pirnt the information of each label
            print("Label: ", label)
            print("Confusion Matrix:\n", class_report)
            print("Accuracy:", accuracy)
            i += 1
        
        

def elapsed_time_decorator(func):
    '''
        We define a function to define a decorator to print the time took in executing a function
    '''
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed_time = time.time() - start_time
        print('Elapsed Time: ', time.strftime("%H:%M:%S", time.gmtime(elapsed_time)))
        return result
    return wrapper


# execute the function below inside this decorator
@elapsed_time_decorator
def model_fit_pred(model, X_train, X_test, Y_train):
    '''
    USAGE 
           define a function to fit a model and make the predictions.
           It will print the time elapsed in the process
    INPUT
           model: model we wanted to train
           X_train, Y_train: data to train the model
           X_test: data to evaluate the model         
    OUTPUT
           Y_pred: labels predicted in the X_test 
    '''
    print('Training model...')
    model.fit(X_train, Y_train)
    print('Evaluating model...')
    Y_pred = model.predict(X_test)
    return Y_pred
    
def save_model(model, model_filepath):
    ''' 
    Saving model's best_estimator_ using pickle
    '''
    pickle.dump(model, open(model_filepath, 'wb'))


def main():
    # check the correct number of arguments
    if len(sys.argv) == 3:
        
        # we give the user the option to choose between two models
        models_num = ['1', '2', '3']
        models_name = ['LinearCSV', 'RandomForests', 'RandomForests_Complete']
        model_option = ''
        
        # ask user to choose a model to train
        while not (model_option in models_num or model_option in models_name):
            print('Choose a model to train:')
            model_option = input('Type (LinearCSV(1) RandomForests(2) RandomForests_Complete(3)):\n')
            
        database_filepath, model_filepath = sys.argv[1:]
        print('Loading data...\n    DATABASE: {}'.format(database_filepath))
        # load the database data
        X, Y, labels = load_data(database_filepath)
        
        # split the data in train and test parts
        X_train_1, X_test_1, Y_train, Y_test = train_test_split(X, Y, test_size=0.2)
        
        # depending on the option selected by the user we train one moel or
        # other
        if (model_option == 'LinearCSV' or model_option == '1'):
            print('Building model...')
            X_train = X_train_1.message.values
            X_test = X_test_1.message.values
            model = model_pipeline_svc_gs()
        elif (model_option == 'RandomForests' or model_option == '2'):
            print('Building model...')
            X_train = X_train_1.message.values
            X_test = X_test_1.message.values
            model = model_pipeline_rf_gs()
        elif (model_option == 'RandomForests_Complete' or model_option == '3'):
            print('Building model...')
            X_train = X_train_1
            X_test = X_test_1
            model = model_pipeline_rf_complete()
        
        # fit and predict with the model
        Y_pred = model_fit_pred(model, X_train, X_test, Y_train)
        
        # save and show in a plot the results for precision, recall, f1-score
        results = display_results(Y_test, Y_pred, labels)
        show_plot(results)
        results.to_csv("./models/results.csv", index=False)
        
        # save the model in a file to use it later
        print('Saving model...\n    MODEL: {}'.format(model_filepath))
        save_model(model, model_filepath)

        print('Trained model saved!')

    else:
        print('Please provide the filepath of the disaster messages database '\
              'as the first argument and the filepath of the pickle file to '\
              'save the model to as the second argument. \n\nExample: python '\
              'train_classifier.py ../data/DisasterResponse.db classifier.pkl')


if __name__ == '__main__':
    main()