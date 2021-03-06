from math import sqrt
from sklearn.metrics import mean_squared_error
from sklearn.tree import DecisionTreeRegressor
from sklearn.linear_model import LinearRegression
from sklearn.neural_network.multilayer_perceptron import MLPRegressor
from sklearn.model_selection import train_test_split, GridSearchCV, LeaveOneOut
from sklearn import metrics
from modules import datahandler, graph_factory
import numpy as np


# Abbreviations of external modules
dth = datahandler
graph = graph_factory


class Data:
    """
    Class datatype allows for mutatable variables
    """
    arthroplasty_dataset = list(dth.load_dataframe('db.csv'))  # the original file TODO probs useless
    dataset_features = list(dth.Data.dataframe)
    # dt_regressor = dth.load_file('dt-regressor.sav')
    # mlp_regressor = dth.load_file('mlp-regressor.sav')
    recalibrate = False
    decision_tree_hyperparameters = {}


# Splits the dataset into two parts - one for training, one for testing, with a split of 65% of the dataset used for
# training and the remaining 35% for testing. Returns training and testing data to be fitted by the model.
# In order to ensure that a certain amont of test case subjects from the dataset (the first 20 or so) are evenly split
def split_dataset_into_train_test(dataframe, column, recalibrate=False):
    """
    Incorporates scikit-learns train_test_split method. The column parameter is a string representing the column name that 
    the split will be based on.
    """
    x = dataframe.drop(column, axis=1)
    y = dataframe[column]

    # Create a training/testing split
    if recalibrate:
        print('recalibrate is turned on')
        x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.20, random_state=33)
    else:
        x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.15)

    """
    # This is a method specific to PARETO dataset that should (in theory) make sure that at least some (and not too many)
    # of the control group samples are included in the split
    while (len(x.loc[x['case'] == 0].index) / 2.2) > len(x_train.loc[x_train['case'] == 0].index) > \
            len(x.loc[x['case'] == 0].index) / 1.5:
        print('\n', 'RECALIBRATING', '\n')
        x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.35)
        
    """

    return x_train, x_test, y_train, y_test


def float_test():
    """
    Generates a list containing numbers ranging from 0.01 to 0.99, was used for hyperparameter tuning of MLP model.
    """
    float_list = []
    x = 0.01
    y = 1.0
    while x < y:
        float_list.append(x)
        x += 0.01
    return float_list


def split_dataset_loocv(dataframe, column):
    """
    Doesn't actually return anything. It was solved manually, so this can be disregarded (or expanded upon).
    """
    x = dataframe.drop(column, axis=1)
    y = dataframe[column]
    loo = LeaveOneOut()
    loo.get_n_splits(x)


def target_predict_decision_tree(target, recalibrate=False, count=0):
    """
    Function for predicting the longevity of a single sample - given the training/testing dataset and a new CSV file
    containing the exact same features as the training/testing set.
    
    Target is a pandas dataframe. Make sure it has the same columns as the training/testing dataset.
    """
    
    # split dataset into training and testing (based on yearsinvivo)
    x_train, x_test, y_train, y_test = split_dataset_into_train_test(dth.prune_features(dth.Data.dataframe),
                                                                     'years in vivo', recalibrate)
    
    # if yearsinvivo is absent - major malfunction. Stop everything.
    if 'years in vivo' not in target:
        return False, False, False

    # Adjust the target prediction to same format as training data
    target_pred = target.drop('years in vivo', axis=1)
    r2 = 0.0

    # Used for calibration of hyperparameters. Tuning can take ages - each parameters value is cross-validated
    # against all other parameters so runtime can become immense. Runtime is calculated as the number of values in
    # parameter X, times the number of values in parameter Y, times ... values in parameter N.
    if recalibrate:
        parameters = {
            'criterion': ('mse', 'friedman_mse', 'mae'),
            'splitter': ('best', 'random'),
            'max_depth': (2, 3, 5, 8, 12, 16, 18, 22, 35),
            'min_samples_split': (2, 3, 4, 5, 6, 9, 11, 16, 21, 25, 38),
            'max_leaf_nodes': range(4, 15),
            'min_impurity_decrease': (0.0, 0.01, 0.02, 0.03, 0.05, 0.08, 0.12, 0.16, 0.2, 0.28, 0.4, 0.8),
            'presort': (True, False)
            # 'random_state': range(0, 101)
        }
        regressor = GridSearchCV(DecisionTreeRegressor(random_state=55), parameters, n_jobs=-1)
        
        # Fit model to data using the best regression model from GridSearchCV, print the optimal parameters, save it
        # to file and save parameters to file.
        regressor.fit(x_train, y_train)
        print(regressor.best_params_)
        print('R2 is: ' + str(regressor.best_score_))
        dth.save_file('DTRegressionBestParams.sav', regressor.best_params_)
        r2 = str(regressor.best_score_)

    else:
        # Use the best parameters found during testing. These are the best according to testing done in october 2018.
        regressor = DecisionTreeRegressor(criterion='mae', max_depth=3, min_samples_split=21, splitter='best',
                                          max_leaf_nodes=4, min_impurity_decrease=0.0, presort=True)
        regressor.fit(x_train, y_train)

    r2_prediction = regressor.predict(x_test)
    prediction = regressor.predict(target_pred)

    if recalibrate:
        # Save results of calibration as a variable.
        dth.TestData.result_dt[str(count)] = {"R2": str(regressor.best_score_), "prediction": str(prediction[0]),
                                               "parameters": regressor.best_params_}
    else:
        # Calculate R2 score.
        y_true = y_test.values.reshape(-1, 1)
        r2_pred = r2_prediction.reshape(-1, 1)
        r2 = metrics.r2_score(y_true, r2_pred)

    return prediction, r2


def target_predict_mlp(target, recalibrate=False, count=0):
    """
    Very similar to above method, uses Multi-Layer Perceptron instead of decision trees.
    """
    x_train, x_test, y_train, y_test = split_dataset_into_train_test(dth.prune_features(dth.Data.dataframe),
                                                                     'years in vivo', recalibrate=False)
    target_pred = target
    target_pred = target_pred.drop('years in vivo', axis=1)
    r2 = 0.0

    if recalibrate:
        parameters = {
            # 'hidden_layer_sizes': [x for x in itertools.product((10, 15, 20, 25, 30, 40, 45, 50, 55, 60), repeat=1)],
            # 'hidden_layer_sizes': [x for x in itertools.product((10, 20, 25, 30, 40, 45, 50, 55, 60), repeat=3)],
            # 'hidden_layer_sizes': [x for x in itertools.product((10, 20, 30, 40, 50, 60, 70, 80), repeat=4)],
            'activation': ('identity', 'logistic', 'tanh', 'relu'),
            # 'max_iter': range(100, 300),
            'alpha': (0.0000, 0.0001, 0.0002, 0.0003, 0.0004, 0.0005, 0.0006, 0.0007, 0.0008, 0.001, 0.0015, 0.0025),
            'early_stopping': (True, False)
        }
        regressor = GridSearchCV(MLPRegressor(activation='tanh', alpha=0.001, early_stopping=True,
                                              hidden_layer_sizes=(25, 20, 40), solver='lbfgs', max_iter=100,
                                              random_state=22), parameters, n_jobs=-1)

        regressor.fit(x_train, y_train)
        print(regressor.best_params_)
        print('R2 is: ' + str(regressor.best_score_))
        dth.save_file('MLPRegressionBestParams.sav', regressor.best_params_)
        r2 = regressor.best_score_
    else:
        regressor = MLPRegressor(activation='tanh', alpha=0.001, early_stopping=True, hidden_layer_sizes=(25, 20, 40),
                                 solver='lbfgs', max_iter=100,)
        regressor.fit(x_train, y_train)

    r2_prediction = regressor.predict(x_test)
    prediction = regressor.predict(target_pred)

    if recalibrate:
        dth.TestData.result_dt[str(count)] = {"R2": str(regressor.best_score_), "prediction": str(prediction[0]), "parameters": regressor.best_params_}
    else:
        y_true = y_test.values.reshape(-1, 1)
        r2_pred = r2_prediction.reshape(-1, 1)
        r2 = metrics.r2_score(y_true, r2_pred)

    return prediction, r2


def target_predict_linear(target, recalibrate=False, count=0):
    """
    This function is used by the user system, and is the primary prediction module for the entire system.
    Target is a dataframe object, recalibrate triggers parameter tuning (unneccessary) and count is for
    keeping track of multiple runs.
    """
    
    # Commented out lines are data preprocessing using minmaxscaler to align all values in the dataframe as they can
    # differ quite a lot.
    # vivo_scaler, scaler = MinMaxScaler(), MinMaxScaler()
    df = dth.prune_features(dth.Data.unprocessed_dataframe)
    # tgt = target
    # df[list(df)] = scaler.fit_transform(df[list(df)])
    # vivo_scaler.fit(tgt['years in vivo'].values.reshape(-1, 1))
    # tgt[list(tgt)] = scaler.transform(tgt[list(tgt)])

    # Split data into training and testing, based on years in vivo.
    x_train, x_test, y_train, y_test = split_dataset_into_train_test(df, 'years in vivo', recalibrate=False)
    # target_pred = tgt.drop('years in vivo', axis=1)
    target_pred = target.drop('years in vivo', axis=1)
    r2 = 0.0

    # Disregard this whole block :)
    if recalibrate:
        parameters = {
            'fit_intercept': (True, False),
            'normalize': (True, False)
        }

        regressor = GridSearchCV(LinearRegression(), parameters, n_jobs=-1)
        regressor.fit(x_train, y_train)
        print(regressor.best_params_)
        print('R2 is: ' + str(regressor.best_score_))
        dth.save_file('LinearRegressionBestParams.sav', regressor.best_params_)
        r2 = regressor.best_score_
    else:
        regressor = LinearRegression(fit_intercept=True)
        regressor.fit(x_train, y_train)
        
    # The magic prediction calling!
    r2_prediction = regressor.predict(x_test)
    prediction = regressor.predict(target_pred)
    # prediction = np.array(regressor.predict(target_pred))
    # prediction = vivo_scaler.inverse_transform(prediction.reshape(1, -1))

    # Saves parameters from tuning to variable
    if recalibrate:
        dth.TestData.result_dt[str(count)] = {"R2": str(regressor.best_score_), "prediction": str(prediction[0]),
                                              "parameters": regressor.best_params_}
        
    # Calculates R2 for prediction, reshapes the values of testing and prediction dataframes to 2d numpy array
    y_true = y_test.values.reshape(-1, 1)
    r2_pred = r2_prediction.reshape(-1, 1)
    r2 = metrics.r2_score(y_true, r2_pred)

    # All metrics available - Adjusted R2 ('r2') is calculated first. RMSE is added as well :)
    eval_metrics = {'r2': 1 - (1 - r2) * (len(y_train) - 1) / (len(y_train) - x_train.shape[1] - 1),
                    'rmse': sqrt(mean_squared_error(y_true, r2_pred))}

    # Calculates the equation for linear regression.
    equation = [regressor.intercept_]
    for x, reg in enumerate(x_train.columns):
        equation.append({'regressor': reg})
        equation.append({'coefficient': regressor.coef_[x]})

    return prediction, eval_metrics, equation


def leave_one_out(control_group=False):
    """
    Function for testing leave one out dataset splitting on the dataset, running predictions for each sample 
    using decision tree regression and calculating the resulting R2 score by passing the true values and 
    predicted values to scikit-learns R2 calculation function
    """
    if control_group:
        data = dth.prune_features(dth.Data.dataframe.head(17))
    else:
        data = dth.prune_features(dth.Data.dataframe)
    targets = np.array(data['years in vivo'])
    dataset = np.array(data.drop('years in vivo', axis=1))

    loo = LeaveOneOut()
    ytests, ypreds, r2yt, r2yp = [], [], [], []

    for train, test in loo.split(dataset):
        x_train, x_test = dataset[train], dataset[test]
        y_train, y_test = targets[train], targets[test]

        regressor = DecisionTreeRegressor(criterion='mae', max_depth=3, min_samples_split=21, splitter='best',
                                          max_leaf_nodes=4, min_impurity_decrease=0.0, presort=True)
        regressor.fit(x_train, y_train)
        prediction = regressor.predict(x_test)

        r2yt.append(y_test)
        r2yp.append(prediction)
        ytests.append(float(y_test))
        ypreds.append(float(prediction))

    r2 = metrics.r2_score(r2yt, r2yp)

    return ytests, ypreds, r2


def multiple_regression_analysis(control_group=False):
    """
    Leave one out function using Multiple Linear Regression instead of decision trees.
    """
    if control_group:
        data = dth.prune_features(dth.Data.dataframe.head(17))
    else:
        data = dth.prune_features(dth.Data.dataframe)

    targets = np.array(data['years in vivo'])
    dataset = np.array(data.drop('years in vivo', axis=1))

    loo = LeaveOneOut()
    ytests, ypreds, r2yt, r2yp = [], [], [], []

    for train, test in loo.split(dataset):
        x_train, x_test = dataset[train], dataset[test]
        y_train, y_test = targets[train], targets[test]

        regressor = LinearRegression()
        regressor.fit(x_train, y_train)
        prediction = regressor.predict(X=x_test)

        r2yt.append(y_test)
        r2yp.append(prediction)
        ytests.append(float(y_test))
        ypreds.append(float(prediction))

    r2 = metrics.r2_score(r2yt, r2yp)
    return ytests, ypreds, r2


def feature_significance(df, target_column):
    feature_p = {}

    """ This stopped working, and I can't for the life of me figure out why.
    
    if target_column in df:
        for feature in list(df):
            if feature != target_column:
                _, feature_p[feature] = f_regression(df[feature].values.reshape(-1, 1), df[target_column])
                """
    return feature_p
