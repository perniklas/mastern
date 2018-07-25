from sklearn.tree import DecisionTreeRegressor
from sklearn.neural_network import multilayer_perceptron as mlp
from sklearn.model_selection import train_test_split, GridSearchCV
import pandas as pd
from sklearn import metrics
from modules import datahandler, graph_factory

dth = datahandler
graph = graph_factory

drop_features_regression = ['id', 'volwear', 'volwearrate']
# These are removed - do not remove Case

parameters = {'splitter': ('best', 'random'),
              'max_depth': range(1, 10),
              'min_samples_split': range(2, 10),
              'min_samples_leaf': range(1, 5)}

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

    x_train = x_train.drop('case', axis=1)
    x_test = x_test.drop('case', axis=1)

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
    print(png)

    return result, r2


# Function for predicting the longevity of a single sample - given the training/testing dataset and a new CSV file
# containing the exact same features as the training/testing set.
def target_predict_longevity(target):
    """     OLD DATA HANDLING
    x_train, x_test, y_train, y_test, regressor = validate_or_create_decision_tree_regressor()
    difference = np.setdiff1d(list(target), list(x_train))
    for item in difference:
        print('difference in features: ', item)
        if item != 'years in vivo':
            target = target.drop(item, axis=1)

    # Actual prediction
    """
    x_train, x_test, y_train, y_test = split_dataset_into_train_test(dth.Data.dataframe, 'years in vivo')
    regressor = GridSearchCV(DecisionTreeRegressor(), parameters, refit=True)
    regressor.fit(x_train, y_train)
    target_pred = target.drop('years in vivo',axis=1)
    target_pred = target_pred.drop('case', axis=1)
    y_prediction = regressor.predict(target_pred)
    result = pd.DataFrame({'Actual': target['years in vivo'], 'Predicted': y_prediction})

    r2 = regressor.best_score_
    return result, r2


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


def mlp_regressor():
    x_train, x_test, y_train, y_test = split_dataset_into_train_test(dth.Data.dataframe, 'years in vivo')
    # regressor = GridSearchCV(mlp.MLPRegressor)  TODO maybe not, as runtime is immense
    regressor = mlp.MLPRegressor(solver='lbfgs', random_state=0)
    regressor.fit(x_train, y_train)
    prediction = regressor.predict(x_test)
    result = pd.DataFrame({'Actual': y_test, 'Predicted': prediction})

    y_true = y_test.values.reshape(-1, 1)
    y_pred = prediction.reshape(-1, 1)
    r2 = metrics.r2_score(y_true, y_pred)

    graph.save_regression_scatter_as_png(regressor, y_test, prediction)

    return result, r2