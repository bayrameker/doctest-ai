"""
Database models for the Test Scenario Generator application.
"""
import os
import uuid
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSON, UUID

db = SQLAlchemy()

def configure_db(app):
    """
    Configure the database for the application.
    """
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        # PostgreSQL expects postgres:// URLs for SQLAlchemy 1.4+
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True,  # Verify connections before using them
            'pool_recycle': 300,    # Recycle connections after 5 minutes
            'pool_timeout': 30,     # Connection acquisition timeout
            'connect_args': {'connect_timeout': 10}  # PostgreSQL connection timeout
        }
        db.init_app(app)
        
        # Create tables if they don't exist
        with app.app_context():
            db.create_all()
    else:
        # Log a warning if no database URL is provided
        import logging
        logging.warning("No DATABASE_URL environment variable found. Database features disabled.")

class Document(db.Model):
    """
    Represents uploaded documents for test scenario generation.
    """
    __tablename__ = 'documents'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = db.Column(db.String(255), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    content_preview = db.Column(db.Text)
    file_type = db.Column(db.String(10))
    content_size = db.Column(db.Integer)  # Size in bytes
    
    # Relationship with scenarios
    scenarios = db.relationship('TestScenarioSet', backref='document', lazy=True)
    
    def __repr__(self):
        return f"<Document {self.filename}>"

class TestScenarioSet(db.Model):
    """
    Represents a set of test scenarios generated from a document.
    """
    __tablename__ = 'test_scenario_sets'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = db.Column(UUID(as_uuid=True), db.ForeignKey('documents.id'), nullable=False)
    ai_model = db.Column(db.String(50), nullable=False)
    generated_date = db.Column(db.DateTime, default=datetime.utcnow)
    summary = db.Column(db.Text)
    
    # Scenarios stored as JSON
    scenarios_data = db.Column(JSON)
    
    # Statistics
    total_scenarios = db.Column(db.Integer)
    total_test_cases = db.Column(db.Integer)
    
    # Parser information
    parser_used = db.Column(db.String(50))
    
    def __repr__(self):
        return f"<TestScenarioSet for document {self.document_id}>"
    
    @property
    def scenarios(self):
        """Return scenarios from JSON data"""
        if self.scenarios_data and 'scenarios' in self.scenarios_data:
            return self.scenarios_data['scenarios']
        return []

class ScenarioAnalytics(db.Model):
    """
    Stores analytics data for generated test scenarios.
    """
    __tablename__ = 'scenario_analytics'
    
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scenario_set_id = db.Column(UUID(as_uuid=True), db.ForeignKey('test_scenario_sets.id'), nullable=False)
    
    # Analytics data
    category_distribution = db.Column(JSON)  # Distribution of scenarios by category
    complexity_distribution = db.Column(JSON)  # Distribution by complexity (simple, medium, complex)
    coverage_score = db.Column(db.Float, default=100.0)  # Estimated coverage (0-100%) - Default: 100%
    content_quality_score = db.Column(db.Float, default=95.0)  # İçerik kalitesi puanı (0-100%) - Default: 95%
    feature_coverage_ratio = db.Column(db.Float, default=1.0)  # Özellik kapsama oranı (0-1) - Default: 1.0
    image_analysis_score = db.Column(db.Float, default=100.0)  # Görsel analiz kapsama puanı - Default: 100%
    
    # Analysis date
    analysis_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    scenario_set = db.relationship('TestScenarioSet', backref=db.backref('analytics', uselist=False))
    
    def __repr__(self):
        return f"<ScenarioAnalytics for set {self.scenario_set_id}>"