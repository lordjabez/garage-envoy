
angular.module('garageEnvoyApp', ['ionic'])


.run(function($ionicPlatform) {
  $ionicPlatform.ready(function() {
    if (window.cordova && window.cordova.plugins.Keyboard) {
      cordova.plugins.Keyboard.hideKeyboardAccessoryBar(true);
    }
    if (window.StatusBar) {
      StatusBar.styleDefault();
    }
  });
})


.controller('mainCtrl', ['$scope', '$http', '$timeout', function($scope, $http, $timeout) {

  $scope.triggerLabel = 'Trigger Door';

  var pollTimeout;

  var schedulePoll = function(delay) {
    $timeout.cancel(pollTimeout);
    pollTimeout = $timeout(getStateHistory, delay);
  };

  var getStateHistory = function() {
    $http.get('/history?n=20')
      .success(function(data) {
        $scope.history = data.history;
        $scope.state = $scope.history.slice(-1)[0].name;
        switch ($scope.state) {
          case 'open':
          case 'half-open':
            $scope.triggerAction = 'Close Door';
            schedulePoll(5000);
            break;
          case 'closed':
          case 'half-closed':
            $scope.triggerAction = 'Open Door';
            schedulePoll(5000);
            break;
          case 'opening':
            $scope.triggerAction = 'Stop Door';
            schedulePoll(1000);
            break;
          case 'closing':
            $scope.triggerAction = 'Reverse Door';
            schedulePoll(1000);
            break;
        }
      })
      .error(function() {
        delete $scope.history;
        delete $scope.state;
        delete $scope.triggerAction;
        schedulePoll(10000);
      });
    };

  $scope.triggerDoor = function() {
    $http.post('/_trigger');
    schedulePoll(500);
  };

  getStateHistory();

}]);
