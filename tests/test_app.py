"""
Comprehensive tests for the Mergington High School Activities API
"""
import pytest
from fastapi.testclient import TestClient
from src.app import app, activities
import copy


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    global activities
    # Store original state
    original_activities = copy.deepcopy(activities)
    
    yield
    
    # Restore original state after test
    activities.clear()
    activities.update(original_activities)


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_returns_html(self, client):
        """Test that root endpoint returns the main HTML page"""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_success(self, client):
        """Test retrieving all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert isinstance(data, dict)
        assert len(data) > 0
        
        # Verify activity structure
        for activity_name, activity_data in data.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)
    
    def test_get_activities_contains_expected_activities(self, client):
        """Test that response contains expected activities"""
        response = client.get("/activities")
        data = response.json()
        
        # Check for some expected activities
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Basketball Team" in data
    
    def test_get_activities_participant_data(self, client):
        """Test that participant data is included"""
        response = client.get("/activities")
        data = response.json()
        
        # Chess Club should have participants
        assert len(data["Chess Club"]["participants"]) > 0
        assert "michael@mergington.edu" in data["Chess Club"]["participants"]


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_success(self, client):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Basketball Team/signup?email=test@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "test@mergington.edu" in data["message"]
        assert "Basketball Team" in data["message"]
        
        # Verify student was added to activity
        verify_response = client.get("/activities")
        activities_data = verify_response.json()
        assert "test@mergington.edu" in activities_data["Basketball Team"]["participants"]
    
    def test_signup_activity_not_found(self, client):
        """Test signup for non-existent activity"""
        response = client.post(
            "/activities/Nonexistent Activity/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    def test_signup_duplicate_registration(self, client):
        """Test that duplicate signup is prevented"""
        email = "duplicate@mergington.edu"
        activity = "Basketball Team"
        
        # First signup should succeed
        response1 = client.post(f"/activities/{activity}/signup?email={email}")
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(f"/activities/{activity}/signup?email={email}")
        assert response2.status_code == 400
        data = response2.json()
        assert "detail" in data
        assert "already signed up" in data["detail"].lower()
    
    def test_signup_activity_full(self, client):
        """Test that signup fails when activity is full"""
        activity = "Basketball Team"
        
        # Get max participants for Basketball Team
        activities_response = client.get("/activities")
        max_participants = activities_response.json()[activity]["max_participants"]
        
        # Fill up the activity
        for i in range(max_participants):
            response = client.post(
                f"/activities/{activity}/signup?email=student{i}@mergington.edu"
            )
            assert response.status_code == 200
        
        # Try to add one more student - should fail
        response = client.post(
            f"/activities/{activity}/signup?email=overflow@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "full" in data["detail"].lower()
    
    def test_signup_with_special_characters_in_activity_name(self, client):
        """Test signup with URL-encoded activity name"""
        # "Chess Club" with URL encoding
        response = client.post(
            "/activities/Chess%20Club/signup?email=newplayer@mergington.edu"
        )
        assert response.status_code == 200


class TestUnregisterFromActivity:
    """Tests for POST /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_success(self, client):
        """Test successful unregistration from an activity"""
        email = "michael@mergington.edu"
        activity = "Chess Club"
        
        # Verify student is initially registered
        activities_response = client.get("/activities")
        assert email in activities_response.json()[activity]["participants"]
        
        # Unregister student
        response = client.post(f"/activities/{activity}/unregister?email={email}")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        
        # Verify student was removed
        verify_response = client.get("/activities")
        activities_data = verify_response.json()
        assert email not in activities_data[activity]["participants"]
    
    def test_unregister_activity_not_found(self, client):
        """Test unregister from non-existent activity"""
        response = client.post(
            "/activities/Nonexistent Activity/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    def test_unregister_student_not_registered(self, client):
        """Test unregister when student is not registered"""
        response = client.post(
            "/activities/Basketball Team/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "not registered" in data["detail"].lower()
    
    def test_signup_and_unregister_workflow(self, client):
        """Test complete workflow: signup then unregister"""
        email = "workflow@mergington.edu"
        activity = "Swimming Club"
        
        # Signup
        signup_response = client.post(f"/activities/{activity}/signup?email={email}")
        assert signup_response.status_code == 200
        
        # Verify signup
        verify_response = client.get("/activities")
        assert email in verify_response.json()[activity]["participants"]
        
        # Unregister
        unregister_response = client.post(f"/activities/{activity}/unregister?email={email}")
        assert unregister_response.status_code == 200
        
        # Verify unregistration
        final_response = client.get("/activities")
        assert email not in final_response.json()[activity]["participants"]


class TestDataIntegrity:
    """Tests for data integrity and edge cases"""
    
    def test_multiple_students_signup(self, client):
        """Test multiple students can sign up for same activity"""
        activity = "Drama Club"
        emails = [f"student{i}@mergington.edu" for i in range(5)]
        
        for email in emails:
            response = client.post(f"/activities/{activity}/signup?email={email}")
            assert response.status_code == 200
        
        # Verify all students are registered
        activities_response = client.get("/activities")
        participants = activities_response.json()[activity]["participants"]
        for email in emails:
            assert email in participants
    
    def test_student_signup_multiple_activities(self, client):
        """Test that a student can sign up for multiple activities"""
        email = "multi@mergington.edu"
        activities_list = ["Basketball Team", "Swimming Club", "Art Studio"]
        
        for activity in activities_list:
            response = client.post(f"/activities/{activity}/signup?email={email}")
            assert response.status_code == 200
        
        # Verify student is in all activities
        all_activities = client.get("/activities").json()
        for activity in activities_list:
            assert email in all_activities[activity]["participants"]
    
    def test_activity_capacity_tracking(self, client):
        """Test that activity capacity is correctly tracked"""
        activity = "Art Studio"
        
        # Get initial state
        initial_response = client.get("/activities")
        initial_count = len(initial_response.json()[activity]["participants"])
        max_participants = initial_response.json()[activity]["max_participants"]
        
        # Add students up to capacity
        slots_available = max_participants - initial_count
        for i in range(slots_available):
            response = client.post(
                f"/activities/{activity}/signup?email=artist{i}@mergington.edu"
            )
            assert response.status_code == 200
        
        # Verify activity is now full
        final_response = client.get("/activities")
        final_count = len(final_response.json()[activity]["participants"])
        assert final_count == max_participants


class TestEdgeCases:
    """Tests for edge cases and error handling"""
    
    def test_email_format_flexibility(self, client):
        """Test that different email formats are accepted"""
        emails = [
            "simple@mergington.edu",
            "first.last@mergington.edu",
            "student+tag@mergington.edu",
            "123numeric@mergington.edu"
        ]
        
        activity = "Science Club"
        for email in emails:
            response = client.post(f"/activities/{activity}/signup?email={email}")
            assert response.status_code == 200
    
    def test_activity_name_with_spaces(self, client):
        """Test activities with spaces in names"""
        activities_with_spaces = ["Chess Club", "Programming Class", "Gym Class"]
        
        for activity in activities_with_spaces:
            response = client.post(
                f"/activities/{activity}/signup?email=test@mergington.edu"
            )
            # Should work (either 200 or 400 for duplicate)
            assert response.status_code in [200, 400]
    
    def test_concurrent_signups(self, client):
        """Test behavior with concurrent signup attempts"""
        activity = "Debate Team"
        emails = [f"concurrent{i}@mergington.edu" for i in range(10)]
        
        # Simulate concurrent signups
        responses = [
            client.post(f"/activities/{activity}/signup?email={email}")
            for email in emails
        ]
        
        # All should succeed (activity has capacity)
        for response in responses:
            assert response.status_code == 200
