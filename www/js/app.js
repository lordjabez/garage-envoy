(function() {


  // Always a good idea
  'use strict';


  // Create the main angular module
  angular.module('garageEnvoyApp', ['ionic'])


  // This app is simple enough to have only one controller
  .controller('mainCtrl', ['$scope', '$http', '$timeout', function($scope, $http, $timeout) {

    // Hanging on to the timeout object allows it to be cancelled when rescheduled.
    var pollTimeout;

    // Cancel the previous scheduled poll and make
    // a new one. The delay value is in milliseconds.
    var schedulePoll = function(delay) {
      $timeout.cancel(pollTimeout);
      pollTimeout = $timeout(getStateHistory, delay);
    };

    // Grab the state history from the server.
    var getStateHistory = function() {
      $http.get('/history?n=20')
        .success(function(data) {
          // Store the history list and latest state (if
          // it exists, it'll be the last item in the list).
          $scope.history = data.history;
          if ($scope.history.length) {
            $scope.state = $scope.history.slice(-1)[0].name;
          }
          else {
            delete $scope.state;
          }
          // Determine what the trigger button will do given the
          // state. Also vary the rate of the next poll, since if
          // the door is moving polls should happen more frequently.
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
            default:
              schedulePoll(10000);
          }
        })
        // If something goes wrong clear out all previous data.
        .error(function() {
          delete $scope.history;
          delete $scope.state;
          delete $scope.triggerAction;
          schedulePoll(10000);
        });
    };

    // Send a trigger message to the server. Since this likely
    // causes a state change, poll again almost right away.
    $scope.triggerDoor = function() {
      $http.post('/_trigger');
      schedulePoll(1000);
    };

    // Get the ball rolling with an initial poll.
    getStateHistory();

  }]);


}());
