"""
Database models for storing startup data.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Table, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()

# association table for many-to-many relationship between startups and investors
startup_investor = Table(
    'startup_investor',
    Base.metadata,
    Column('startup_id', Integer, ForeignKey('startups.id'), primary_key=True),
    Column('investor_id', Integer, ForeignKey('investors.id'), primary_key=True)
)

# association table for many-to-many relationship between startups and key people
startup_key_person = Table(
    'startup_key_person',
    Base.metadata,
    Column('startup_id', Integer, ForeignKey('startups.id'), primary_key=True),
    Column('key_person_id', Integer, ForeignKey('key_people.id'), primary_key=True)
)


class Startup(Base):
    """Startup database model."""
    __tablename__ = 'startups'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    funding_amount = Column(String(100), nullable=True)
    funding_round = Column(String(100), nullable=True)
    funding_date = Column(DateTime, nullable=True, index=True)
    industry = Column(String(255), nullable=True, index=True)
    location = Column(String(255), nullable=True, index=True)
    company_size = Column(String(100), nullable=True)
    company_url = Column(String(255), nullable=True)
    linkedin_url = Column(String(255), nullable=True)
    source = Column(String(255), nullable=True)
    source_url = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    
    # relationships
    investors = relationship("Investor", secondary=startup_investor, back_populates="startups")
    key_people = relationship("KeyPerson", secondary=startup_key_person, back_populates="startups")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert startup to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "funding_amount": self.funding_amount,
            "funding_round": self.funding_round,
            "funding_date": self.funding_date.isoformat() if self.funding_date else None,
            "industry": self.industry,
            "location": self.location,
            "company_size": self.company_size,
            "company_url": self.company_url,
            "linkedin_url": self.linkedin_url,
            "source": self.source,
            "source_url": self.source_url,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "investors": [investor.name for investor in self.investors],
            "key_people": [
                {
                    "name": person.name,
                    "title": person.title,
                    "linkedin_url": person.linkedin_url,
                    "email": person.email
                }
                for person in self.key_people
            ]
        }


class Investor(Base):
    """Investor database model."""
    __tablename__ = 'investors'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    website = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    
    # relationships
    startups = relationship("Startup", secondary=startup_investor, back_populates="investors")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert investor to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "website": self.website,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class KeyPerson(Base):
    """Key person database model."""
    __tablename__ = 'key_people'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    title = Column(String(255), nullable=True)
    linkedin_url = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    
    # relationships
    startups = relationship("Startup", secondary=startup_key_person, back_populates="key_people")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert key person to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "title": self.title,
            "linkedin_url": self.linkedin_url,
            "email": self.email,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
