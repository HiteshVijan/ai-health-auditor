"""Add pricing intelligence tables

Revision ID: 001_pricing
Revises: 
Create Date: 2024-12-12

This migration adds:
- hospitals: Hospital profiles for pricing intelligence
- procedures: Master procedure catalog with CGHS/PMJAY mappings
- price_points: Crowdsourced price observations
- hospital_scores: Historical hospital scoring records
- price_contributions: User contribution tracking for gamification
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite


# revision identifiers, used by Alembic.
revision = '001_pricing'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create hospitals table
    op.create_table(
        'hospitals',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('normalized_name', sa.String(255), nullable=False),
        sa.Column('aliases', sa.Text(), nullable=True),
        sa.Column('city', sa.String(100), nullable=False),
        sa.Column('state', sa.String(100), nullable=False),
        sa.Column('pincode', sa.String(10), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('hospital_type', sa.Enum('government', 'cghs_empaneled', 'private', 'corporate', 'nabh_accredited', 'trust', 'unknown', name='hospitaltype'), nullable=False),
        sa.Column('city_tier', sa.Enum('metro', 'tier_1', 'tier_2', 'tier_3', 'unknown', name='citytier'), nullable=False),
        sa.Column('is_cghs_empaneled', sa.Boolean(), default=False, nullable=True),
        sa.Column('is_nabh_accredited', sa.Boolean(), default=False, nullable=True),
        sa.Column('is_pmjay_empaneled', sa.Boolean(), default=False, nullable=True),
        sa.Column('pricing_score', sa.Float(), default=50.0, nullable=True),
        sa.Column('transparency_score', sa.Float(), default=50.0, nullable=True),
        sa.Column('overall_score', sa.Float(), default=50.0, nullable=True),
        sa.Column('total_bills_analyzed', sa.Integer(), default=0, nullable=True),
        sa.Column('total_procedures_priced', sa.Integer(), default=0, nullable=True),
        sa.Column('avg_overcharge_percent', sa.Float(), default=0.0, nullable=True),
        sa.Column('gstin', sa.String(20), nullable=True),
        sa.Column('website', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('is_verified', sa.Boolean(), default=False, nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('normalized_name', 'city', name='uq_hospital_name_city'),
    )
    op.create_index('ix_hospitals_id', 'hospitals', ['id'])
    op.create_index('ix_hospitals_name', 'hospitals', ['name'])
    op.create_index('ix_hospitals_normalized_name', 'hospitals', ['normalized_name'])
    op.create_index('ix_hospitals_city', 'hospitals', ['city'])
    op.create_index('ix_hospitals_state', 'hospitals', ['state'])
    op.create_index('ix_hospitals_hospital_type', 'hospitals', ['hospital_type'])
    op.create_index('ix_hospitals_city_tier', 'hospitals', ['city_tier'])
    op.create_index('ix_hospitals_is_cghs_empaneled', 'hospitals', ['is_cghs_empaneled'])
    op.create_index('ix_hospital_location', 'hospitals', ['city', 'state'])
    op.create_index('ix_hospital_scores', 'hospitals', ['pricing_score', 'overall_score'])

    # Create procedures table
    op.create_table(
        'procedures',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('normalized_name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('subcategory', sa.String(100), nullable=True),
        sa.Column('cghs_code', sa.String(50), nullable=True),
        sa.Column('pmjay_code', sa.String(50), nullable=True),
        sa.Column('cpt_code', sa.String(20), nullable=True),
        sa.Column('icd10_code', sa.String(20), nullable=True),
        sa.Column('cghs_rate', sa.Float(), nullable=True),
        sa.Column('cghs_max_private', sa.Float(), nullable=True),
        sa.Column('pmjay_package_rate', sa.Float(), nullable=True),
        sa.Column('market_low', sa.Float(), nullable=True),
        sa.Column('market_median', sa.Float(), nullable=True),
        sa.Column('market_high', sa.Float(), nullable=True),
        sa.Column('market_p25', sa.Float(), nullable=True),
        sa.Column('market_p75', sa.Float(), nullable=True),
        sa.Column('price_point_count', sa.Integer(), default=0, nullable=True),
        sa.Column('last_price_update', sa.DateTime(timezone=True), nullable=True),
        sa.Column('aliases', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_procedures_id', 'procedures', ['id'])
    op.create_index('ix_procedures_name', 'procedures', ['name'])
    op.create_index('ix_procedures_normalized_name', 'procedures', ['normalized_name'], unique=True)
    op.create_index('ix_procedures_category', 'procedures', ['category'])
    op.create_index('ix_procedures_cghs_code', 'procedures', ['cghs_code'])
    op.create_index('ix_procedures_pmjay_code', 'procedures', ['pmjay_code'])
    op.create_index('ix_procedure_category', 'procedures', ['category', 'subcategory'])
    op.create_index('ix_procedure_codes', 'procedures', ['cghs_code', 'pmjay_code'])

    # Create price_points table
    op.create_table(
        'price_points',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('procedure_id', sa.Integer(), nullable=False),
        sa.Column('hospital_id', sa.Integer(), nullable=True),
        sa.Column('charged_amount', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(3), default='INR', nullable=False),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('state', sa.String(100), nullable=True),
        sa.Column('hospital_type', sa.Enum('government', 'cghs_empaneled', 'private', 'corporate', 'nabh_accredited', 'trust', 'unknown', name='hospitaltype'), nullable=True),
        sa.Column('city_tier', sa.Enum('metro', 'tier_1', 'tier_2', 'tier_3', 'unknown', name='citytier'), nullable=True),
        sa.Column('source', sa.Enum('cghs', 'pmjay', 'user_bill', 'hospital_website', 'insurance_claim', 'survey', 'scraped', 'manual', name='pricesource'), nullable=False),
        sa.Column('source_document_id', sa.Integer(), nullable=True),
        sa.Column('contributing_user_id', sa.Integer(), nullable=True),
        sa.Column('observation_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('confidence', sa.Float(), default=0.5, nullable=True),
        sa.Column('is_verified', sa.Boolean(), default=False, nullable=True),
        sa.Column('is_outlier', sa.Boolean(), default=False, nullable=True),
        sa.Column('cghs_comparison', sa.Float(), nullable=True),
        sa.Column('pmjay_comparison', sa.Float(), nullable=True),
        sa.Column('market_comparison', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['procedure_id'], ['procedures.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['hospital_id'], ['hospitals.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['source_document_id'], ['documents.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['contributing_user_id'], ['users.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_price_points_id', 'price_points', ['id'])
    op.create_index('ix_price_points_procedure_id', 'price_points', ['procedure_id'])
    op.create_index('ix_price_points_hospital_id', 'price_points', ['hospital_id'])
    op.create_index('ix_price_points_city', 'price_points', ['city'])
    op.create_index('ix_price_points_source', 'price_points', ['source'])
    op.create_index('ix_price_point_procedure_hospital', 'price_points', ['procedure_id', 'hospital_id'])
    op.create_index('ix_price_point_location', 'price_points', ['city', 'state'])
    op.create_index('ix_price_point_source_date', 'price_points', ['source', 'observation_date'])

    # Create hospital_scores table
    op.create_table(
        'hospital_scores',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('hospital_id', sa.Integer(), nullable=False),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('pricing_score', sa.Float(), nullable=False),
        sa.Column('transparency_score', sa.Float(), nullable=False),
        sa.Column('consistency_score', sa.Float(), nullable=False),
        sa.Column('overall_score', sa.Float(), nullable=False),
        sa.Column('bills_analyzed', sa.Integer(), default=0, nullable=True),
        sa.Column('procedures_priced', sa.Integer(), default=0, nullable=True),
        sa.Column('avg_overcharge_percent', sa.Float(), default=0.0, nullable=True),
        sa.Column('overcharge_frequency', sa.Float(), default=0.0, nullable=True),
        sa.Column('score_breakdown', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['hospital_id'], ['hospitals.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_hospital_scores_id', 'hospital_scores', ['id'])
    op.create_index('ix_hospital_scores_hospital_id', 'hospital_scores', ['hospital_id'])
    op.create_index('ix_hospital_score_period', 'hospital_scores', ['hospital_id', 'period_start', 'period_end'])

    # Create price_contributions table
    op.create_table(
        'price_contributions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=True),
        sa.Column('price_points_added', sa.Integer(), default=0, nullable=True),
        sa.Column('hospitals_added', sa.Integer(), default=0, nullable=True),
        sa.Column('procedures_added', sa.Integer(), default=0, nullable=True),
        sa.Column('verified_count', sa.Integer(), default=0, nullable=True),
        sa.Column('accuracy_score', sa.Float(), default=0.5, nullable=True),
        sa.Column('contribution_type', sa.String(50), default='bill_upload', nullable=True),
        sa.Column('points_earned', sa.Integer(), default=0, nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_price_contributions_id', 'price_contributions', ['id'])
    op.create_index('ix_price_contributions_user_id', 'price_contributions', ['user_id'])


def downgrade() -> None:
    op.drop_table('price_contributions')
    op.drop_table('hospital_scores')
    op.drop_table('price_points')
    op.drop_table('procedures')
    op.drop_table('hospitals')

