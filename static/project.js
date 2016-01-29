// TODO: remove PROJECT_NAME, USER_ID references

refreshProjectFiles(PROJECT_NAME);

function API(URL, success, error) {
  $.ajax({
    url: '/api/' + URL, type: 'GET', dataType: 'json', success: success, error: error,
    beforeSend: function (xhr) {
      xhr.setRequestHeader('authorization', API_TOKEN);
    }
  });
}

function refreshProjectFiles(projectName) {
  API('project/' + projectName + '/', function (data) {
    $('#project-file-list').empty();
    var div = $('#project-file-list');
    for (var i = 0; i < data.length; i++) {
      var childDiv = $('#project-file-template').clone();
      childDiv.removeAttr('id');
      var anchor = childDiv.find('a');
      //anchor.attr('href', projectPath + '/play/' + 'index.html');
      //anchor.text(JSON.stringify(data[i]));
      anchor.text(data[i].name);
      /*

      var header = childDiv.find(':header');
      header.html(projectName + ' <a href="three.js/editor/index.html#app=https://storage.googleapis.com/zig/' +
          projectPath + '/app.json">(edit)</a>\n' +
          ' <a href="#" onclick="publishProject(\'' + projectName + '\')">(publish)</a>\n')
      */
      div.append(childDiv);
    }
  });
}

function publishProject(projectName) {
  API('publish/' + projectName, function (data) {
    console.log('return from api/publish: ' + data);
    window.open('http://all.spiffthings.com/' + USER_ID +'/' + projectName + '/index.html', projectName);
  }, function (data) {
    console.log('error from api/publish');
  });
}

function uploadFormData(formId) {
  var formData = new FormData(document.getElementById(formId));
  $.ajax({
    url: '/api/project/' + PROJECT_NAME + '/',
    type: 'POST',
    data: formData,
    enctype: 'multipart/form-data',
    processData: false,  // tell jQuery not to process the data
    contentType: false,   // tell jQuery not to set contentType
    beforeSend: function (xhr) {
      xhr.setRequestHeader('authorization', API_TOKEN);
    }
  }).done(function(data) {
    console.log(data);
    refreshProjectFiles(PROJECT_NAME);
  });
}
