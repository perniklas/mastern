import itertools

from sklearn.tree import DecisionTreeRegressor
from sklearn.neural_network import multilayer_perceptron as mlp
from sklearn.model_selection import train_test_split, GridSearchCV
import pandas as pd
from sklearn import metrics
from modules import datahandler, graph_factory

dth = datahandler
graph = graph_factory

drop_features_regression = ['id', 'cupx', 'cupy', 'volwear', 'volwearrate', 'cupx', 'cupy']
# These are removed - do not remove Case

"""
    List of all features in the dataset
    'id', 'case', 'cuploose', 'stemloose', 'years in vivo', 'cr', 'co', 'zr', 'ni', 'mb', 'linwear', 'linwearrate', 
    'volwear', 'volwearrate', 'inc', 'ant', 'cupx', 'cupy', 'male', 'female'
"""


class Data:
    arthroplasty_dataset = list(dth.load_dataframe('db.csv'))  # the original file TODO probs useless
    dataset_features = list(dth.Data.dataframe)
    dt_regressor = dth.load_pickle_file('dt-regressor.sav')
    mlp_regressor = dth.load_pickle_file('mlp-regressor.sav')


# Takes two parameters; dataframe contains the dataset to be split into testing and training datasets, and column is
# the variable that determines the split
# TODO manipulate split
def split_dataset_into_train_test(dataframe, column):
    x = dataframe.drop(column, axis=1)
    y = dataframe[column]

    # Create a training/testing split
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.35, random_state=55)

    # TODO might not be necessary - just in case there's too little or too much of control cases in the
    # TODO training/testing subset. Not optimal by any means, just a temporary solution.
    while (len(x.loc[x['case'] == 0].index) / 2.2) > len(x_train.loc[x_train['case'] == 0].index) > \
            len(x.loc[x['case'] == 0].index) / 1.5:
        print('\n', 'RECALIBRATING', '\n')
        x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.35)

    return x_train, x_test, y_train, y_test


# Function for predicting the longevity of test set. Modify this to work on a singular entry (as with the target
# regress).
def predict_longevity():
    x_train, x_test, y_train, y_test, regressor = validate_or_create_regressor('dt-regressor.sav')
    y_prediction = regressor.predict(x_test)

    result = pd.DataFrame({'Actual': y_test, 'Predicted': y_prediction})

    # Reshape the arrays to work with R2 score validator1
    y_true = y_test.values.reshape(-1, 1)
    y_pred = y_prediction.reshape(-1, 1)
    r2 = metrics.r2_score(y_true, y_pred)

    png = graph.save_regression_scatter_as_png(regressor, y_test, y_prediction)

    return result, r2


# Function for predicting the longevity of a single sample - given the training/testing dataset and a new CSV file
# containing the exact same features as the training/testing set.
def target_predict_longevity(target, recalibrate=False):

    # For each parameter value range, multiply that value with the next and the next and so on, split the result by:
    # i7-3770k at 4.8GHz - divide by 136 to get the seconds required to run the test.
    parameters = {
        # 'criterion': ('mse', 'friedman_mse', 'mae'),
        'splitter': ('best', 'random'),
        'max_depth': range(1, 4),
        'min_samples_split':  range(10, 13),  # iterates from 0.01 to 0.99
        'max_leaf_nodes': range(2, 5),
        'min_impurity_decrease': (0.0, 0.01, 0.02, 0.04),
        'presort': (True, False)
    }

    target = prune_features(target)
    df = prune_features(dth.Data.dataframe)

    x_train, x_test, y_train, y_test = split_dataset_into_train_test(df, 'years in vivo')
    regressor = GridSearchCV(DecisionTreeRegressor(random_state=33), parameters, refit=True)
    regressor.fit(x_train, y_train)

    # TODO for use with random_state=none
    # while regressor.best_score_ < 0.29:
    #    print('recalibrating')
    #    regressor = GridSearchCV(DecisionTreeRegressor(), parameters, refit=True)
    #    regressor.fit(x_train, y_train)

    target_pred = target.drop('years in vivo', axis=1)
    y_prediction = regressor.predict(target_pred)

    print(regressor.best_params_)
    print('R2 is: ' + str(regressor.best_score_))

    dth.save_file('DTregressorbestparams.sav', regressor.best_params_)

    return pd.DataFrame({'Actual': target['years in vivo'], 'Predicted': y_prediction}), regressor.best_score_


def float_test():
    float_list = []
    x = 0.01
    y = 1.0
    while x < y:
        float_list.append(x)
        x += 0.01
    return float_list


# Loads a previously saved regression model if there is one, trains a new if there's not. If the dataframe being used
#  for the prediction have more or less features than the regression model,
def validate_or_create_regressor(filename):
    df = dth.Data.dataframe
    x_train, x_test, y_train, y_test = split_dataset_into_train_test(df, 'years in vivo')

    # Checks whether the feature length of the dataset is the same as the model features, retrain model if not
    if dth.load_pickle_file(filename) is not None:
        regressor = dth.load_pickle_file(filename)
    else:
        regressor = update_regression_model(filename, x_train, y_train)

    # Checks whether the amount of features in the regression model is the same as the data being used to predict a
    # feature. TODO create save-new-model so I don't have to deal with retraining the model every time? Or handle better
    if regressor.max_features_ == len(list(x_test)):
        return x_train, x_test, y_train, y_test, regressor
    else:
        regressor = update_regression_model(filename, x_train, y_train)
        return x_train, x_test, y_train, y_test, regressor


def update_regression_model(filename, x_train, y_train):
    Data.split = dth.Data.split
    if filename == 'dt-regressor.sav':
        regressor = DecisionTreeRegressor(random_state=0)
        regressor.fit(x_train, y_train)
        dth.save_file(filename, regressor)
        print('Saved new regression model as', filename)
        return regressor
    elif filename == 'mlp-regressor.sav':
        regressor = mlp.MLPRegressor(solver='lbfgs', random_state=0)
        regressor.fit(x_train, y_train)
        dth.save_file(filename, regressor)
        print('Saved new regression model as', filename)
        return regressor
    else:
        print('Wrong filetype?')


def mlp_regressor(target):
    # According to the dataset I've been given, these are the best parameters for MLP
    # activation='logistic', alpha=0.0001, early_stopping=True, hidden_layer_sizes=(50, 40, 60, 80), solver='lbfgs,
    # max_iter=195'

    # - hidden_layer_sizes=(50, 40, 60, 80) when full unprocessed dataset
    # - hidden_layer_sizes=(50, 50, 70, 60) for processed (pruned) dataset

    parameters = {
        # 'hidden_layer_sizes': [x for x in itertools.product((10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60), repeat=1)],
        # 'hidden_layer_sizes': [x for x in itertools.product((10, 20, 25, 30, 40, 45, 50, 55, 60), repeat=2)],
        # 'hidden_layer_sizes': [x for x in itertools.product((30, 40, 50, 60, 70, 80), repeat=4)],
        # 'activation': ('identity', 'logistic', 'tanh', 'relu'),
        # 'max_iter': range(150, 300),
        # 'alpha': (0.0000, 0.0001, 0.0002, 0.0003, 0.0004, 0.0005, 0.0006, 0.0007),
        # 'early_stopping': (True, False)
    }

    target = prune_features(target)
    df = prune_features(dth.Data.dataframe)

    x_train, x_test, y_train, y_test = split_dataset_into_train_test(df, 'years in vivo')
    regressor = GridSearchCV(mlp.MLPRegressor(activation='logistic', early_stopping=True, alpha=0.0001,
                                              hidden_layer_sizes=(50, 50, 70, 60), solver='lbfgs', max_iter=195,
                                              random_state=33), parameters)
    regressor.fit(x_train, y_train)

    target_pred = target.drop('years in vivo', axis=1)
    prediction = regressor.predict(target_pred)

    # graph.save_regression_scatter_as_png(regressor, y_test, prediction)

    print(regressor.best_params_)
    print('R2 is: ' + str(regressor.best_score_))

    dth.save_file('mlpbestscorefullparams.sav', regressor.best_params_)

    return pd.DataFrame({'Actual': target['years in vivo'], 'Predicted': prediction}), regressor.best_score_


def prune_features(df):
    for feature in drop_features_regression:
        if feature in df:
            df = df.drop(feature, axis=1)
    return df
