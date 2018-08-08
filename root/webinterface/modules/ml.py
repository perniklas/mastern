import itertools

from sklearn.tree import DecisionTreeRegressor
from sklearn.linear_model import LinearRegression
from sklearn.neural_network.multilayer_perceptron import MLPRegressor
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
        regressor = update_regression_model(filename)

    # Checks whether the amount of features in the regression model is the same as the data being used to predict a
    # feature. TODO create save-new-model so I don't have to deal with retraining the model every time? Or handle better
    if regressor.max_features_ == len(list(x_test)):
        return regressor
    else:
        regressor = update_regression_model(filename)
        return regressor


def update_regression_model(filename):
    Data.split = dth.Data.split
    if filename == 'dt-regressor.sav':
        regressor = DecisionTreeRegressor(random_state=0)
        dth.save_file(filename, regressor)
        print('Saved new regression model as', filename)
        return regressor
    elif filename == 'mlp-regressor.sav':
        regressor = MLPRegressor(activation='logistic', early_stopping=True, alpha=0.0001,
                                 hidden_layer_sizes=(50, 50, 70, 60), solver='lbfgs', max_iter=195)
        dth.save_file(filename, regressor)
        print('Saved new regression model as', filename)
        return regressor
    elif filename == 'linear-regressor.sav':
        regressor = LinearRegression(fit_intercept=True, normalize=True, copy_X=True)
        dth.save_file(filename, regressor)
        print('Saved new regression model as', filename)
        return regressor
    else:
        print('Wrong filetype?')


# Function for predicting the longevity of a single sample - given the training/testing dataset and a new CSV file
# containing the exact same features as the training/testing set.
def target_predict_decision_tree(target, recalibrate=False):
    target = prune_features(target)
    df = prune_features(dth.Data.dataframe)
    x_train, x_test, y_train, y_test = split_dataset_into_train_test(df, 'years in vivo')
    target_pred = target.drop('years in vivo', axis=1)

    if recalibrate:
        parameters = {
            'criterion': ('mse', 'friedman_mse', 'mae'),
            'splitter': ('best', 'random'),
            'max_depth': range(1, 7),
            'min_samples_split': range(3, 9),  # TODO need to make more iterations with less vlaues
            'max_leaf_nodes': range(2, 8),
            'min_impurity_decrease': (0.0, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.1, 0.11, 0.12, 0.13,
                                       0.14),
            'presort': (True, False),
            # 'random_state': range(0, 101)
        }
        # 'criterion': 'mae', 'max_depth': 1, 'max_leaf_nodes': 2, 'min_impurity_decrease': 0.0, 'min_samples_split': 7, 'presort': True, 'splitter': 'random' randomstate 48
        # 'criterion': 'mse', 'max_depth': 1, 'max_leaf_nodes': 3, 'min_impurity_decrease': 0.0, 'min_samples_split': 11, 'presort': True, 'splitter': 'random' randomstate 33
        # {'criterion': 'mae', 'max_depth': 1, 'max_leaf_nodes': 2, 'min_impurity_decrease': 0.0, 'min_samples_split': 3, 'presort': True, 'splitter': 'random'} - 22 score, 48 random
        regressor = GridSearchCV(DecisionTreeRegressor(random_state=48), parameters, refit=True)
    else:
        regressor = validate_or_create_regressor('dt-regressor.sav')

    regressor.fit(x_train, y_train)
    r2_prediction = regressor.predict(x_test)
    y_prediction = regressor.predict(target_pred)

    if recalibrate:
        print(regressor.best_params_)
        print('R2 is: ' + str(regressor.best_score_))
        dth.save_file('DTRegressionBestParams.sav', regressor.best_params_)
        r2 = regressor.best_score_
    else:
        y_true = y_test.values.reshape(-1, 1)
        r2_pred = r2_prediction.reshape(-1, 1)
        r2 = metrics.r2_score(y_true, r2_pred)

    return pd.DataFrame({'Actual': target['years in vivo'], 'Predicted': y_prediction}), r2


def target_predict_mlp(target, recalibrate=False):
    target = prune_features(target)
    df = prune_features(dth.Data.dataframe)
    x_train, x_test, y_train, y_test = split_dataset_into_train_test(df, 'years in vivo')
    target_pred = target.drop('years in vivo', axis=1)

    if recalibrate:
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
        regressor = GridSearchCV(MLPRegressor(activation='logistic', early_stopping=True, alpha=0.0001,
                                              hidden_layer_sizes=(50, 50, 70, 60), solver='lbfgs', max_iter=195,
                                              random_state=33), parameters)
    else:
        regressor = validate_or_create_regressor('mlp-regressor.sav')

    regressor.fit(x_train, y_train)
    r2_prediction = regressor.predict(x_test)
    prediction = regressor.predict(target_pred)

    if recalibrate:
        print(regressor.best_params_)
        print('R2 is: ' + str(regressor.best_score_))
        dth.save_file('MLPRegressionBestParams.sav', regressor.best_params_)
        r2 = regressor.best_score_
    else:
        y_true = y_test.values.reshape(-1, 1)
        r2_pred = r2_prediction.reshape(-1, 1)
        r2 = metrics.r2_score(y_true, r2_pred)

    return pd.DataFrame({'Actual': target['years in vivo'], 'Predicted': prediction}), r2


def target_predict_linear(target, recalibrate=False):
    # Preprocessing the data
    target = prune_features(target)
    target_pred = target.drop('years in vivo', axis=1)
    df = prune_features(dth.Data.dataframe)
    x_train, x_test, y_train, y_test = split_dataset_into_train_test(df, 'years in vivo')

    if recalibrate:
        parameters = {
            'fit_intercept': (True, False),
            'normalize': (True, False),
            'copy_X': (True, False)
        }

        regressor = GridSearchCV(LinearRegression(), parameters, refit=True)
    else:
        regressor = LinearRegression()

    regressor.fit(x_train, y_train)
    r2_prediction = regressor.predict(x_test)
    y_prediction = regressor.predict(target_pred)

    if recalibrate:
        print(regressor.best_params_)
        print('R2 is: ' + str(regressor.best_score_))
        dth.save_file('LinearRegressionBestParams.sav', regressor.best_params_)
        r2 = regressor.best_score_
    else:
        y_true = y_test.values.reshape(-1, 1)
        r2_pred = r2_prediction.reshape(-1, 1)
        r2 = metrics.r2_score(y_true, r2_pred)

    # graph_factory.save_regression_scatter_as_png(df['years in vivo'], y_prediction)

    return pd.DataFrame({'Actual': target['years in vivo'], 'Predicted': y_prediction}), r2


def prune_features(df):
    for feature in drop_features_regression:
        if feature in df:
            df = df.drop(feature, axis=1)
    return df
