"""
Database storage and retrieval functionality for startup data.
"""
import logging
import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple, Union

from sqlalchemy import create_engine, desc, func
from sqlalchemy.orm import sessionmaker, Session

from src.data_collection.base import StartupData
from src.data_storage.models import Base, Startup, Investor, KeyPerson

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manager for database operations."""
    
    def __init__(self, db_path: str = "sqlite:///data/startups.db"):
        """
        Initialize the database manager.
        
        Args:
            db_path: SQLAlchemy database URL
        """
        # ensure the data directory exists for file-based databases
        if db_path.startswith("sqlite:///") and not db_path.startswith("sqlite:///:memory:"):
            db_file = db_path.replace("sqlite:///", "")
            if db_file and os.path.dirname(db_file):  # Only create dirs if there's a path
                os.makedirs(os.path.dirname(db_file), exist_ok=True)
            
        self.engine = create_engine(db_path)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # create tables if they don't exist
        Base.metadata.create_all(self.engine)
        logger.info(f"Database initialized at {db_path}")
    
    def get_session(self) -> Session:
        """
        Get a database session.
        
        Returns:
            SQLAlchemy session
        """
        return self.SessionLocal()
    
    def save_startup_data(self, startup_data: Union[StartupData, List[StartupData]]) -> None:
        """
        Save startup data to the database.
        
        Args:
            startup_data: StartupData object or list of StartupData objects
        """
        if isinstance(startup_data, StartupData):
            startup_data = [startup_data]
            
        with self.get_session() as session:
            for data in startup_data:
                try:
                    # check if startup already exists
                    existing_startup = session.query(Startup).filter(Startup.name == data.name).first()
                    
                    if existing_startup:
                        # update existing startup
                        self._update_existing_startup(session, existing_startup, data)
                    else:
                        # create new startup
                        self._create_new_startup(session, data)
                        
                except Exception as e:
                    logger.error(f"Error saving startup {data.name}: {e}")
                    session.rollback()
                    continue
                    
            session.commit()
    
    def _create_new_startup(self, session: Session, data: StartupData) -> Startup:
        """
        Create a new startup record.
        
        Args:
            session: Database session
            data: StartupData object
            
        Returns:
            Created Startup object
        """
        # create the startup
        startup = Startup(
            name=data.name,
            description=data.description,
            funding_amount=data.funding_amount,
            funding_round=data.funding_round,
            funding_date=data.funding_date,
            industry=data.industry,
            location=data.location,
            company_size=data.company_size,
            company_url=data.company_url,
            linkedin_url=data.linkedin_url,
            source=data.source,
            source_url=data.source_url,
            created_at=data.created_at,
            updated_at=data.updated_at
        )
        
        session.add(startup)
        session.flush()  # Flush to get the ID
        
        # add investors
        if data.investors:
            for investor_name in data.investors:
                investor = self._get_or_create_investor(session, investor_name)
                startup.investors.append(investor)
        
        # add key people
        if data.key_people:
            for person_data in data.key_people:
                key_person = self._get_or_create_key_person(
                    session,
                    name=person_data.get("name", ""),
                    title=person_data.get("title"),
                    linkedin_url=person_data.get("linkedin_url"),
                    email=person_data.get("email")
                )
                startup.key_people.append(key_person)
                
        return startup
    
    def _update_existing_startup(self, session: Session, startup: Startup, data: StartupData) -> Startup:
        """
        Update an existing startup record.
        
        Args:
            session: Database session
            startup: Existing Startup object
            data: New StartupData object
            
        Returns:
            Updated Startup object
        """
        # update non-null fields
        if data.description:
            startup.description = data.description
            
        if data.funding_amount:
            startup.funding_amount = data.funding_amount
            
        if data.funding_round:
            startup.funding_round = data.funding_round
            
        if data.funding_date:
            startup.funding_date = data.funding_date
            
        if data.industry:
            startup.industry = data.industry
            
        if data.location:
            startup.location = data.location
            
        if data.company_size:
            startup.company_size = data.company_size
            
        if data.company_url:
            startup.company_url = data.company_url
            
        if data.linkedin_url:
            startup.linkedin_url = data.linkedin_url
            
        if data.source:
            # append new source if different
            if startup.source and data.source not in startup.source:
                startup.source = f"{startup.source}, {data.source}"
            else:
                startup.source = data.source
                
        if data.source_url:
            startup.source_url = data.source_url
            
        # update timestamp
        startup.updated_at = datetime.now()
        
        # add new investors
        if data.investors:
            existing_investor_names = [investor.name for investor in startup.investors]
            for investor_name in data.investors:
                if investor_name not in existing_investor_names:
                    investor = self._get_or_create_investor(session, investor_name)
                    startup.investors.append(investor)
        
        # add new key people
        if data.key_people:
            existing_person_names = [person.name for person in startup.key_people]
            for person_data in data.key_people:
                person_name = person_data.get("name", "")
                if person_name and person_name not in existing_person_names:
                    key_person = self._get_or_create_key_person(
                        session,
                        name=person_name,
                        title=person_data.get("title"),
                        linkedin_url=person_data.get("linkedin_url"),
                        email=person_data.get("email")
                    )
                    startup.key_people.append(key_person)
                    
        return startup
    
    def _get_or_create_investor(self, session: Session, name: str) -> Investor:
        """
        Get or create an investor.
        
        Args:
            session: Database session
            name: Investor name
            
        Returns:
            Investor object
        """
        investor = session.query(Investor).filter(Investor.name == name).first()
        if not investor:
            investor = Investor(name=name)
            session.add(investor)
            session.flush()
            
        return investor
    
    def _get_or_create_key_person(
        self,
        session: Session,
        name: str,
        title: Optional[str] = None,
        linkedin_url: Optional[str] = None,
        email: Optional[str] = None
    ) -> KeyPerson:
        """
        Get or create a key person.
        
        Args:
            session: Database session
            name: Person name
            title: Person title
            linkedin_url: LinkedIn URL
            email: Email address
            
        Returns:
            KeyPerson object
        """
        key_person = session.query(KeyPerson).filter(KeyPerson.name == name).first()
        if not key_person:
            key_person = KeyPerson(
                name=name,
                title=title,
                linkedin_url=linkedin_url,
                email=email
            )
            session.add(key_person)
            session.flush()
        else:
            # update non-null fields
            if title and not key_person.title:
                key_person.title = title
                
            if linkedin_url and not key_person.linkedin_url:
                key_person.linkedin_url = linkedin_url
                
            if email and not key_person.email:
                key_person.email = email
                
        return key_person
    
    def get_startups(
        self,
        months_back: int = 3,
        industries: Optional[List[str]] = None,
        locations: Optional[List[str]] = None,
        funding_rounds: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get startups from the database with filtering.
        
        Args:
            months_back: Number of months to look back
            industries: List of industries to filter by
            locations: List of locations to filter by
            funding_rounds: List of funding rounds to filter by
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of startup dictionaries
        """
        with self.get_session() as session:
            query = session.query(Startup)
            
            # apply date filter
            if months_back > 0:
                date_threshold = datetime.now() - timedelta(days=30 * months_back)
                query = query.filter(Startup.funding_date >= date_threshold)
                
            # apply industry filter
            if industries:
                query = query.filter(Startup.industry.in_(industries))
                
            # apply location filter
            if locations:
                query = query.filter(Startup.location.in_(locations))
                
            # apply funding round filter
            if funding_rounds:
                query = query.filter(Startup.funding_round.in_(funding_rounds))
                
            # order by funding date (most recent first)
            query = query.order_by(desc(Startup.funding_date))
            
            # apply pagination
            query = query.limit(limit).offset(offset)
            
            # execute query
            startups = query.all()
            
            # convert to dictionaries
            return [startup.to_dict() for startup in startups]
    
    def get_startup_by_id(self, startup_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a startup by ID.
        
        Args:
            startup_id: Startup ID
            
        Returns:
            Startup dictionary or None if not found
        """
        with self.get_session() as session:
            startup = session.query(Startup).filter(Startup.id == startup_id).first()
            return startup.to_dict() if startup else None
    
    def get_startup_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a startup by name.
        
        Args:
            name: Startup name
            
        Returns:
            Startup dictionary or None if not found
        """
        with self.get_session() as session:
            startup = session.query(Startup).filter(Startup.name == name).first()
            return startup.to_dict() if startup else None
    
    def get_industries(self) -> List[str]:
        """
        Get all unique industries.
        
        Returns:
            List of industry names
        """
        with self.get_session() as session:
            industries = session.query(Startup.industry).distinct().filter(Startup.industry != None).all()
            return [industry[0] for industry in industries if industry[0]]
    
    def get_locations(self) -> List[str]:
        """
        Get all unique locations.
        
        Returns:
            List of location names
        """
        with self.get_session() as session:
            locations = session.query(Startup.location).distinct().filter(Startup.location != None).all()
            return [location[0] for location in locations if location[0]]
    
    def get_funding_rounds(self) -> List[str]:
        """
        Get all unique funding rounds.
        
        Returns:
            List of funding round names
        """
        with self.get_session() as session:
            rounds = session.query(Startup.funding_round).distinct().filter(Startup.funding_round != None).all()
            return [round[0] for round in rounds if round[0]]
    
    def get_startup_count(self) -> int:
        """
        Get the total number of startups.
        
        Returns:
            Startup count
        """
        with self.get_session() as session:
            return session.query(func.count(Startup.id)).scalar()
    
    def get_investor_count(self) -> int:
        """
        Get the total number of investors.
        
        Returns:
            Investor count
        """
        with self.get_session() as session:
            return session.query(func.count(Investor.id)).scalar()
    
    def get_funding_date_range(self) -> Tuple[Optional[datetime], Optional[datetime]]:
        """
        Get the range of funding dates.
        
        Returns:
            Tuple of (min_date, max_date)
        """
        with self.get_session() as session:
            min_date = session.query(func.min(Startup.funding_date)).scalar()
            max_date = session.query(func.max(Startup.funding_date)).scalar()
            return (min_date, max_date)
    
    def get_startups_by_month(self, months_back: int = 12) -> Dict[str, int]:
        """
        Get startup counts grouped by month.
        
        Args:
            months_back: Number of months to look back
            
        Returns:
            Dictionary mapping month strings to startup counts
        """
        with self.get_session() as session:
            # calculate the date threshold
            date_threshold = datetime.now() - timedelta(days=30 * months_back)
            
            # this query is sqlite-specific
            # for other databases, the date extraction would be different
            results = session.query(
                func.strftime("%Y-%m", Startup.funding_date).label("month"),
                func.count(Startup.id).label("count")
            ).filter(
                Startup.funding_date >= date_threshold
            ).group_by(
                func.strftime("%Y-%m", Startup.funding_date)
            ).all()
            
            return {result.month: result.count for result in results if result.month}
    
    def get_startups_by_industry(self, limit: int = 10) -> Dict[str, int]:
        """
        Get startup counts grouped by industry.
        
        Args:
            limit: Maximum number of industries to return
            
        Returns:
            Dictionary mapping industry names to startup counts
        """
        with self.get_session() as session:
            results = session.query(
                Startup.industry,
                func.count(Startup.id).label("count")
            ).filter(
                Startup.industry != None
            ).group_by(
                Startup.industry
            ).order_by(
                desc("count")
            ).limit(limit).all()
            
            return {result.industry: result.count for result in results if result.industry}
    
    def get_startups_by_location(self, limit: int = 10) -> Dict[str, int]:
        """
        Get startup counts grouped by location.
        
        Args:
            limit: Maximum number of locations to return
            
        Returns:
            Dictionary mapping location names to startup counts
        """
        with self.get_session() as session:
            results = session.query(
                Startup.location,
                func.count(Startup.id).label("count")
            ).filter(
                Startup.location != None
            ).group_by(
                Startup.location
            ).order_by(
                desc("count")
            ).limit(limit).all()
            
            return {result.location: result.count for result in results if result.location}
    
    def get_startups_by_funding_round(self) -> Dict[str, int]:
        """
        Get startup counts grouped by funding round.
        
        Returns:
            Dictionary mapping funding round names to startup counts
        """
        with self.get_session() as session:
            results = session.query(
                Startup.funding_round,
                func.count(Startup.id).label("count")
            ).filter(
                Startup.funding_round != None
            ).group_by(
                Startup.funding_round
            ).order_by(
                desc("count")
            ).all()
            
            return {result.funding_round: result.count for result in results if result.funding_round}
    
    def clean_old_data(self, months_to_keep: int = 3) -> int:
        """
        Remove startups older than the specified number of months.
        
        Args:
            months_to_keep: Number of months of data to keep
            
        Returns:
            Number of startups removed
        """
        with self.get_session() as session:
            # calculate the date threshold
            date_threshold = datetime.now() - timedelta(days=30 * months_to_keep)
            
            # find startups to delete
            startups_to_delete = session.query(Startup).filter(
                Startup.funding_date < date_threshold
            ).all()
            
            count = len(startups_to_delete)
            
            # delete the startups
            for startup in startups_to_delete:
                session.delete(startup)
                
            session.commit()
            
            return count
