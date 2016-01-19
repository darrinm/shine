refreshUserProjects();

function createProject() {
  $('#create-project-dialog').on('show.bs.modal', function (e) {
    var $dialog = $(this);
    var primaryButton = $(this).find('.btn-primary');
    var selectedItem = null;
    primaryButton.prop('disabled', true);
    $(this).on('item-selected', function (event, item) {
      // Enable the create project button.
      primaryButton.prop('disabled', false);
      selectedItem = item;
    });
    primaryButton.click(function () {
      var templateDir = $(selectedItem).attr('data-name');
      var projectName = templateDir.slice(templateDir.indexOf('/') + 1);

      // Clone template as a new user project.
      $.get('copy?src=' + templateDir + '&dst=' + projectName + '&user-token=fake', function (data) {
        // TODO: busy / progress indicator
        // TODO: error handling
        // refresh user projects
        refreshUserProjects();
        // ? add "Project Name: " input field to dialog?
        //   populate with template name + " Copy [N]"
        // ? select project name for editing?
      });
    });

    getProjectTemplates(function (templates) {
      $('#create-project-dialog .modal-body').empty();
      var div = $('#create-project-dialog .modal-body');

      for (var i = 0; i < templates.length; i++) {
        var templateName = templates[i];
        var templateDir = templateName;
        var childDiv = $('#project-thumbnail-template').clone();
        childDiv.removeAttr('id');
        childDiv.attr('data-name', templateDir);

        childDiv.click(function () {
          $(this).siblings().removeClass('active');
          $(this).addClass('active');
          $(this).trigger('item-selected', [ this ]);
        });
        var header = childDiv.find(':header');
        header.html(templateDir.slice(templateDir.indexOf('/') + 1));
        div.append(childDiv);
      }
    });
  });
  $('#create-project-dialog').modal();
}

function API(URL, success, error) {
  $.ajax({
    url: URL, type: 'GET', dataType: 'json', success: success, error: error,
    beforeSend: function (xhr) {
      xhr.setRequestHeader('authorization', API_TOKEN);
    }
  });
}

function refreshUserProjects() {
  API('api/project', function (data) {
    $('#user-project-list').empty();
    var div = $('#user-project-list');
    for (var i = 0; i < data.length; i++) {
      var projectPath = data[i].substring(0, data[i].length - 1);
      var separatorIndex = data[i].indexOf('/')
      var projectName = projectPath.slice(separatorIndex + 1);
      var childDiv = $('#project-thumbnail-template').clone();
      childDiv.removeAttr('id');
      var anchor = childDiv.find('a');
      anchor.attr('href', projectPath + '/play/' + 'index.html');
      /*
      var img = childDiv.find('img');
      img.attr('src', 'http://placehold.it/130x130');
      //img.attr('src', 'http://fpoimg.com/130x130?text=' + shortNameMinusUser);
      //img.attr('src', 'http://loremflickr.com/130/130?' + shortNameMinusUser);
      */

      var header = childDiv.find(':header');
      header.html(projectName + ' <a href="three.js/editor/index.html#app=https://storage.googleapis.com/zig/' +
          projectPath + '/app.json">(edit)</a>\n');
      div.append(childDiv);
    }
  });
}

function getProjectTemplates(callback) {
  API('api/template', function (data) {
    callback(data)
  });
}

function endsWith(str, suffix) {
  return str.indexOf(suffix, str.length - suffix.length) !== -1;
}
