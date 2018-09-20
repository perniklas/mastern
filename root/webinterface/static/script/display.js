var direction = 'down',
    cancelled,
    patientInfo,
    previousWindow,
    previousWindowButtons;

$(document).ready(function () {
    $('#scienceToggle').hide();
    clearTable();
    loadPage();

    $('#start').show().click(function() {
        start();
        cancelled = false;
    });

    $('#title h1').dblclick(function() {
        $('#scienceToggle').fadeToggle();
    });

    $('#dt').click(function() {
        if (!$(this).hasClass('disabled')) {
            $(this).fadeOut();
            hideAllElements();
            loading();
            $('.result_element').remove();
            $.getJSON('/dt', function (data) {
                if(data == null) {
                    systemStatusBad();
                }
                updateTable(data);
                displayImage(data['graphs']);
                if (!cancelled) {
                    displayResults();
                }
            });
        }
    });

    $('#featurebtn').click(function() {
        hideAllElements();
        loading();
        systemStatusBad();
        $.get('/features', function(input) {
            $('#features').append(input);
            $('#resultheader').text('Dataset features');
            $('#resultcontext').text('These are the features (or columns) of the dataset - also known as the ' +
                'categories of information gathered from each patient.').append("<br /><br />").append('The ' +
                'checkboxes indicate whether or not a feature will be included when the system predicts how long ' +
                'an implant will last in the given patient, by checking a box you include that feature in the ' +
                'prediction.');
            $('#loadinggif').hide();
            $('.feature').fadeIn();
            systemStatusGood();
        });
    });

    $('#saveFeatures').click(function() {
        $.ajax({
            url: '/features',
            data: $('.feat').serialize(),
            type: 'POST',
            success: function(response) {
                console.log(response);
            },
            error: function(response) {
                console.log('Oh no, ' + response.valueOf());
                systemStatusBad();
            }
        });
        $(this).addClass('success').text('Successfully saved');
        setTimeout(nextStep, 2000);
    });

    $('#addtarget').click(function() {
        hideAllElements();
        loading();
        enterPatientInfo();
    });

    $('#case').change(function() {
        if ($(this).val() == '1') {
            $('.hidden').slideDown();
        } else if ($(this).val() == '0') {
            $('.hidden').slideUp();
        }
    });

    $('#saveTarget').click(function() {
        var formValid = true;

        $('#patientInfoForm form input').each(function() {
            if ($(this).val() === "") {
                formValid = false;
                console.log('Missing value!');
                $(this).addClass('emptyForm');
            } else {
                if ($(this).hasClass('emptyForm')) {
                    console.log('yes');
                    $(this).removeClass('emptyForm');
                }
            }
        });
        if (formValid) {
            console.log('running post request');
            patientInfo = $('.patInfo').val();
            console.log(patientInfo);
            $.ajax({
                url: '/updatetarget',
                data: $('.patInfo').serialize(),
                type: 'POST',
                success: function (response) {
                    console.log(response);
                },
                error: function (response) {
                    console.log('Oh no, ' + response.valueOf());
                    systemStatusBad();
                }
            });
            $(this).addClass('success').text('Successfully saved');
            setTimeout(nextStep, 2000);
        }
    });

    $('#cancel').click(function() {
        stopProcess();
        hideAllElements();
        start();
    });

    $('#back').click(function() {
        stopProcess();
        hideAllElements();
        previousWindow(previousWindowButtons);
    });

    $('#r2button').click(function() {
        $('#r2info').fadeToggle();
    });
});

function loading() {
    systemStatusLoading();
    clearTable();
    $('#loadinggif, #cancel, #back, #data').fadeIn();
    $('#resultheader').text('Loading...').fadeIn();
    $('#resultcontext').text('We\'re doing some heavy lifting, this shouldn\'t take too long').fadeIn();
    $('#centercontent').slideDown();
}

function doneLoading() {
    $('#resultheader, #resultcontext, #loadinggif').hide();
}

function loadPage() {
    hideAllElements();
    $('#input, #start').fadeIn();
}

function start() {
    doneLoading();
    $('#start, #cancel, #back').hide();
    direction = 'down';
    $('#menu').css('left', 0);
    setTimeout(systemStatusGood, 800);
    $('#title h1').text('Main menu');
    $('#title p').text('This is the main menu. To get started, we\'re going to need some information about the ' +
        'patient - if you press the big orange button in the middle of the screen you\'ll be able to enter all the ' +
        'necessary patient details.');
    setTimeout(function() {
        displayInput($('#addtarget, #buttons button, #status'));
    }, 1000);
}

function displayInput(buttons) {
    buttons.fadeIn();
    doneLoading();
    $('#saveFeatures').removeClass('success').text('Save feature selection');
    $('#saveTarget').removeClass('success').text('Save patient information');
    clearTable();
    $('#centercontent .input, #data').show();
    if (direction == 'up') {
        $('#centercontent').fadeIn();
    } else {
        $('#centercontent').slideDown();
    }
    systemStatusGood();
}

function enterPatientInfo() {
    doneLoading();
    $('#centercontent').slideDown();
    $('#title h1').text('Patient information form');
    $('#title p').text('We need you to enter all the information on your patient here. If you\'re missing some ' +
        'data, please enter -1.');
    $('#patientInfoForm').show();
    systemStatusGood();
}

function nextStep() {
    doneLoading();
    hideAllElements();
    $('#title h1').text('One last thing...');
    $('#title p').text('We\'re ready to start predicting! The prediction usually takes a minute to run, but that ' +
        'depends on how beefy your computer processor is. It might take longer. If you want, you can specify which ' +
        'parts of the patient information will be taken into consideration - after all, you\'re the most qualified to ' +
        'decide what matters and what doesn\'t.');
    direction = 'up';
    displayInput($('#dt, #featurebtn'));
}

function displayResults() {
    doneLoading();
    $('#title h1').text('Prediction results');
    $('#title p').text('Presented to you in the center part of the page are the results from ' +
        'running your data into the machine learning prediction magician.');
    $('#results_table, #graphFiller, #graphs, #r2button').fadeIn();
}

function displayImage(images) {
    for(var image in images) {
        var img = document.createElement('img');
        img.setAttribute('src', '../static/img/' + images[image]);
        img.setAttribute('class', 'graphImage');
        document.getElementById('graphs').appendChild(img);
    }

    $('#graphFiller').fadeIn();
    systemStatusGood();
}

function updateTable(json) {
    $.each(json, function(index, item) {
        console.log(json[item]);
        console.log(item);
    });
    systemStatusGood();
    if ('r2' in json) {
        $('#r2info').text('This prediction model has an R2 score of ' + parseFloat(json.r2).toFixed(7));
    }
    $.each(json.result, function (index, item) {
        appendDataToTable(item);
    });
}

function appendDataToTable(rowdata) {
    $('#results_table').append(function () {
        return '<tr class="result_element"><td>Actual: ' + rowdata['Actual'] + '</td>' + '\n' +
            '<td>Predicted: ' + rowdata['Predicted'] + '</td></tr>';
    });
}

function stopProcess() {
    $.ajax({
        url: '/stopProcess',
        type: 'POST',
        success: function (response) {
            console.log(response);
            cancelled = true;
        },
        error: function (response) {
            console.log(response);
            systemStatusBad();
        }
    })
}

function systemStatusGood() {
    var status = $('#status');
    if (!status.is(':visible')) {
        status.fadeIn();
    }
    status.css('background-color', '#142914').text('System status: All good.');
}

function systemStatusLoading() {
    var status = $('#status');
    if (!status.is(':visible')) {
        status.fadeIn();
    }
     status.css('background-color', '#30310f').text('System status:    Loading - please wait...');
}

function systemStatusBad() {
    var status = $('#status');
    if (!status.is(':visible')) {
        status.fadeIn();
    }
     status.css('background-color', 'red').text('System status: Something stopped working - please refresh!');
}

function hideAllElements() {
    $('.hideContent, #data, #patientInfoForm, #graphFiller, #graphs, #status, .feature, #loadinggif, #r2info, ' +
        '#r2button, #input, #input button, .input, .input button, .optional').hide();
}

function clearTable() {
    $('#resultheader').text('');
    $('#resultcontext').text('');
    $('.result_element, .graphImage').remove();
    $('#features').empty();
}