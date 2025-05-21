"""
Base collector interface for all data collection methods.
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any


class StartupData:
    """Data structure for storing startup information."""
    
    def __init__(
        self,
        name: str,
        description: str,
        funding_amount: Optional[str] = None,
        funding_round: Optional[str] = None,
        funding_date: Optional[datetime] = None,
        investors: Optional[List[str]] = None,
        industry: Optional[str] = None,
        location: Optional[str] = None,
        company_size: Optional[str] = None,
        company_url: Optional[str] = None,
        linkedin_url: Optional[str] = None,
        key_people: Optional[List[Dict[str, str]]] = None,
        source: Optional[str] = None,
        source_url: Optional[str] = None
    ):
        self.name = name
        self.description = description
        self.funding_amount = funding_amount
        self.funding_round = funding_round
        self.funding_date = funding_date
        self.investors = investors or []
        self.industry = industry
        self.location = location
        self.company_size = company_size
        self.company_url = company_url
        self.linkedin_url = linkedin_url
        self.key_people = key_people or []
        self.source = source
        self.source_url = source_url
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert startup data to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "funding_amount": self.funding_amount,
            "funding_round": self.funding_round,
            "funding_date": self.funding_date.isoformat() if self.funding_date else None,
            "investors": self.investors,
            "industry": self.industry,
            "location": self.location,
            "company_size": self.company_size,
            "company_url": self.company_url,
            "linkedin_url": self.linkedin_url,
            "key_people": self.key_people,
            "source": self.source,
            "source_url": self.source_url,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StartupData':
        """Create startup data from dictionary."""
        funding_date = None
        if data.get("funding_date"):
            try:
                funding_date = datetime.fromisoformat(data["funding_date"])
            except (ValueError, TypeError):
                pass
        
        instance = cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            funding_amount=data.get("funding_amount"),
            funding_round=data.get("funding_round"),
            funding_date=funding_date,
            investors=data.get("investors", []),
            industry=data.get("industry"),
            location=data.get("location"),
            company_size=data.get("company_size"),
            company_url=data.get("company_url"),
            linkedin_url=data.get("linkedin_url"),
            key_people=data.get("key_people", []),
            source=data.get("source"),
            source_url=data.get("source_url")
        )
        
        if data.get("created_at"):
            try:
                instance.created_at = datetime.fromisoformat(data["created_at"])
            except (ValueError, TypeError):
                pass
            
        if data.get("updated_at"):
            try:
                instance.updated_at = datetime.fromisoformat(data["updated_at"])
            except (ValueError, TypeError):
                pass
            
        return instance


class DataCollector(ABC):
    """Base interface for all data collection methods."""
    
    @abstractmethod
    def collect(self, **kwargs) -> List[StartupData]:
        """
        Collect startup data from the source.
        
        Args:
            **kwargs: Additional parameters specific to the collection method.
            
        Returns:
            List of StartupData objects.
        """
        pass
    
    @abstractmethod
    def get_source_name(self) -> str:
        """
        Get the name of the data source.
        
        Returns:
            String name of the data source.
        """
        pass
