
angular.module('garageEnvoyApp', ['ionic'])


.run(function($ionicPlatform) {
  $ionicPlatform.ready(function() {
    if(window.cordova && window.cordova.plugins.Keyboard) {
      cordova.plugins.Keyboard.hideKeyboardAccessoryBar(true);
    }
    if(window.StatusBar) {
      StatusBar.styleDefault();
    }
  });
})


.controller('mainCtrl', ['$scope', '$http', '$timeout', function($scope, $http, $timeout) {

    $scope.triggerLabel = 'Trigger Door';

    var getStateEvents = function() {
        $http.get('/events?t=state&n=10')
            .success(function(data) {
                $scope.stateEvents = data.events;
                state = $scope.stateEvents.slice(-1)[0].name;
                switch (state) {
                    case 'open':
                    case 'half-open':
                        $scope.triggerLabel = 'Close Door';
                        break;
                    case 'closed':
                    case 'half-closed':
                        $scope.triggerLabel = 'Open Door';
                        break;
                    case 'opening':
                    case 'closing':
                        $scope.triggerLabel = 'Stop Door';
                        break;
                }
            });
        $timeout(getStateEvents, 1000);
    }

    $scope.triggerDoor = function() {
        $http.post('/_trigger');
    }

    getStateEvents();

}])
