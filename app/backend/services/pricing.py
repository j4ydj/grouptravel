"""Pricing provider interface and implementations."""
from abc import ABC, abstractmethod
from datetime import date, time, timedelta
from typing import Optional
import random
import hashlib
from functools import lru_cache
import aiohttp
from aiohttp import ClientTimeout
import asyncio
import json
import logging
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, Column, String, Float, DateTime, Text
from sqlalchemy import Integer
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from app.backend.schemas.itinerary import Itinerary, ItinerarySegment
from app.backend.core.config import settings


Base = declarative_base()


class PriceCache(Base):
    """SQLite cache table for pricing results."""
    __tablename__ = "price_cache"
    
    cache_key = Column(String, primary_key=True)
    price = Column(Float)
    airline = Column(String)
    stops = Column(Integer)
    travel_minutes = Column(Integer)
    cached_at = Column(DateTime, default=datetime.utcnow)


# Create cache engine and session (reuse main engine for SQLite)
# For SQLite, we'll use the same engine to share the database file
from app.backend.db.session import engine as main_engine

# Use main engine for cache (shares same SQLite file)
cache_engine = main_engine
# Create cache table if it doesn't exist
PricingBase = Base  # Alias for clarity
PricingBase.metadata.create_all(bind=cache_engine)
CacheSessionLocal = sessionmaker(bind=cache_engine)


class PricingProvider(ABC):
    """Abstract base class for pricing providers."""
    
    @abstractmethod
    async def get_best_itinerary(
        self,
        origin: str,
        destination: str,
        depart_date: date,
        return_date: date,
        constraints: dict
    ) -> Itinerary:
        """
        Get the best itinerary for given parameters.
        
        Args:
            origin: Origin airport IATA code
            destination: Destination airport IATA code
            depart_date: Departure date
            return_date: Return date
            constraints: Additional constraints (travel_class, preferred_airlines, etc.)
        
        Returns:
            Itinerary object
        """
        pass


class MockPricingProvider(PricingProvider):
    """Mock pricing provider with deterministic fake data."""
    
    # Common airline codes
    AIRLINES = ["AA", "UA", "DL", "BA", "LH", "AF", "KL", "LX", "VS", "EK", "QF", "SQ"]
    
    def __init__(self, volatile: bool = False):
        """
        Initialize mock pricing provider.
        
        Args:
            volatile: If True, add small random variation to prices
        """
        self.volatile = volatile
        self._in_memory_cache: dict[str, Itinerary] = {}
    
    def _get_cache_key(
        self,
        origin: str,
        destination: str,
        depart_date: date,
        return_date: date,
        constraints: dict
    ) -> str:
        """Generate cache key."""
        constraint_str = str(sorted(constraints.items()))
        return f"{origin}:{destination}:{depart_date}:{return_date}:{constraint_str}"
    
    def _get_seeded_random(self, seed: str) -> random.Random:
        """Get seeded random number generator for determinism."""
        seed_int = int(hashlib.md5(seed.encode()).hexdigest(), 16)
        return random.Random(seed_int)
    
    def _generate_itinerary(
        self,
        origin: str,
        destination: str,
        depart_date: date,
        return_date: date,
        constraints: dict,
        seed: str
    ) -> Itinerary:
        """Generate a deterministic fake itinerary."""
        rng = self._get_seeded_random(seed)
        
        # Base price calculation
        base_price = 200.0 + (rng.random() * 1800.0)  # $200-$2000
        
        # Adjust for travel class
        travel_class = constraints.get("travel_class", "economy")
        class_multipliers = {
            "economy": 1.0,
            "premium_economy": 1.5,
            "business": 3.0,
            "first": 5.0
        }
        base_price *= class_multipliers.get(travel_class, 1.0)
        
        # Add volatility if enabled
        if self.volatile:
            base_price *= (0.95 + rng.random() * 0.1)  # ±5% variation
        
        # Generate stops (0-2)
        stops = rng.randint(0, 2)
        
        # Generate travel time (200-1200 minutes)
        travel_minutes = 200 + rng.randint(0, 1000)
        
        # Generate times
        depart_hour = rng.randint(6, 22)
        depart_minute = rng.choice([0, 15, 30, 45])
        depart_time = time(depart_hour, depart_minute)
        
        # Arrival time based on travel minutes
        arrive_datetime = datetime.combine(depart_date, depart_time) + timedelta(minutes=travel_minutes)
        arrive_time = arrive_datetime.time()
        
        # Select airline
        airline = rng.choice(self.AIRLINES)
        
        # Generate Concur deep link placeholder
        concur_link = f"https://concur.example.com/book?origin={origin}&dest={destination}&date={depart_date}"
        
        flight_number = f"{airline}{rng.randint(100, 9999)}"

        # Build segments (outbound + return)
        segments: list[ItinerarySegment] = []
        segment_count = stops + 1
        segment_duration = max(int(travel_minutes / segment_count), 30)
        # Outbound segments
        current_origin = origin
        current_depart = datetime.combine(depart_date, depart_time)
        for idx in range(segment_count):
            seg_dest = destination if idx == segment_count - 1 else f"HUB{idx+1}"
            seg_arrive = current_depart + timedelta(minutes=segment_duration)
            segments.append(
                ItinerarySegment(
                    leg="outbound",
                    segment_index=idx,
                    origin=current_origin,
                    destination=seg_dest,
                    depart_time=current_depart.time(),
                    arrive_time=seg_arrive.time(),
                    airline=airline,
                    flight_number=flight_number,
                    duration_minutes=segment_duration
                )
            )
            current_origin = seg_dest
            current_depart = seg_arrive + timedelta(minutes=45)
        # Return segments (mirror)
        return_depart = datetime.combine(return_date, depart_time)
        current_origin = destination
        current_depart = return_depart
        for idx in range(segment_count):
            seg_dest = origin if idx == segment_count - 1 else f"HUBR{idx+1}"
            seg_arrive = current_depart + timedelta(minutes=segment_duration)
            segments.append(
                ItinerarySegment(
                    leg="return",
                    segment_index=idx,
                    origin=current_origin,
                    destination=seg_dest,
                    depart_time=current_depart.time(),
                    arrive_time=seg_arrive.time(),
                    airline=airline,
                    flight_number=flight_number,
                    duration_minutes=segment_duration
                )
            )
            current_origin = seg_dest
            current_depart = seg_arrive + timedelta(minutes=45)

        return Itinerary(
            origin=origin,
            destination=destination,
            depart_date=depart_date,
            return_date=return_date,
            airline=airline,
            flight_number=flight_number,
            stops=stops,
            depart_time=depart_time,
            arrive_time=arrive_time,
            travel_minutes=travel_minutes,
            price=round(base_price, 2),
            concur_deep_link=concur_link,
            segments=segments
        )
    
    async def get_best_itinerary(
        self,
        origin: str,
        destination: str,
        depart_date: date,
        return_date: date,
        constraints: dict
    ) -> Itinerary:
        """Get best itinerary (deterministic mock)."""
        cache_key = self._get_cache_key(origin, destination, depart_date, return_date, constraints)
        
        # Check in-memory cache first
        if cache_key in self._in_memory_cache:
            return self._in_memory_cache[cache_key]
        
        # Check SQLite cache
        db = CacheSessionLocal()
        try:
            cached = db.query(PriceCache).filter_by(cache_key=cache_key).first()
            if cached:
                # Reconstruct itinerary from cache
                itinerary = Itinerary(
                    origin=origin,
                    destination=destination,
                    depart_date=depart_date,
                    return_date=return_date,
                    airline=cached.airline,
                    flight_number=None,
                    stops=cached.stops,
                    depart_time=time(8, 0),  # Default, not cached
                    arrive_time=time(14, 0),  # Default, not cached
                    travel_minutes=cached.travel_minutes,
                    price=cached.price,
                    concur_deep_link=f"https://concur.example.com/book?origin={origin}&dest={destination}&date={depart_date}",
                    segments=[]
                )
                self._in_memory_cache[cache_key] = itinerary
                return itinerary
        finally:
            db.close()
        
        # Generate new itinerary
        seed = f"{origin}{destination}{depart_date}{return_date}{str(constraints)}"
        itinerary = self._generate_itinerary(origin, destination, depart_date, return_date, constraints, seed)
        
        # Cache in memory (LRU with maxsize handled by dict size limit)
        if len(self._in_memory_cache) > 1000:
            # Remove oldest entry (simple FIFO)
            oldest_key = next(iter(self._in_memory_cache))
            del self._in_memory_cache[oldest_key]
        self._in_memory_cache[cache_key] = itinerary
        
        # Cache in SQLite
        db = CacheSessionLocal()
        try:
            cache_entry = PriceCache(
                cache_key=cache_key,
                price=itinerary.price,
                airline=itinerary.airline,
                stops=itinerary.stops,
                travel_minutes=itinerary.travel_minutes
            )
            db.merge(cache_entry)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()
        
        return itinerary


class TravelpayoutsProvider(PricingProvider):
    """Stub for Travelpayouts provider."""
    
    async def get_best_itinerary(
        self,
        origin: str,
        destination: str,
        depart_date: date,
        return_date: date,
        constraints: dict
    ) -> Itinerary:
        """TODO: Implement Travelpayouts integration."""
        raise NotImplementedError("TravelpayoutsProvider not yet implemented")


class DuffelProvider(PricingProvider):
    """Duffel API pricing provider."""
    
    DUFFEL_API_BASE = "https://api.duffel.com"
    
    def __init__(self, api_key: str):
        """
        Initialize Duffel provider.
        
        Args:
            api_key: Duffel API access token
        """
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Duffel-Version": "v2",
            "Content-Type": "application/json"
        }
        self._in_memory_cache: dict[str, Itinerary] = {}
        self.logger = logging.getLogger(__name__)
    
    def _get_cache_key(
        self,
        origin: str,
        destination: str,
        depart_date: date,
        return_date: date,
        constraints: dict
    ) -> str:
        """Generate cache key."""
        constraint_str = str(sorted(constraints.items()))
        return f"duffel:{origin}:{destination}:{depart_date}:{return_date}:{constraint_str}"
    
    async def get_best_itinerary(
        self,
        origin: str,
        destination: str,
        depart_date: date,
        return_date: date,
        constraints: dict
    ) -> Itinerary:
        """
        Get best itinerary from Duffel API with caching and fallback.
        
        Args:
            origin: Origin IATA code
            destination: Destination IATA code
            depart_date: Departure date
            return_date: Return date
            constraints: Additional constraints
        
        Returns:
            Itinerary object
        """
        cache_key = self._get_cache_key(origin, destination, depart_date, return_date, constraints)
        
        # Check in-memory cache first
        if cache_key in self._in_memory_cache:
            return self._in_memory_cache[cache_key]
        
        # Check SQLite cache
        db = CacheSessionLocal()
        try:
            cached = db.query(PriceCache).filter_by(cache_key=cache_key).first()
            if cached:
                # Reconstruct itinerary from cache
                itinerary = Itinerary(
                    origin=origin,
                    destination=destination,
                    depart_date=depart_date,
                    return_date=return_date,
                    airline=cached.airline,
                    stops=cached.stops,
                    depart_time=time(8, 0),  # Default, not cached
                    arrive_time=time(14, 0),  # Default, not cached
                    travel_minutes=cached.travel_minutes,
                    price=cached.price,
                    concur_deep_link=f"https://concur.example.com/book?origin={origin}&dest={destination}&date={depart_date}"
                )
                self._in_memory_cache[cache_key] = itinerary
                return itinerary
        finally:
            db.close()
        
        # Cache miss - try Duffel API with fallback to mock
        try:
            itinerary = await self._fetch_from_duffel_api(
                origin, destination, depart_date, return_date, constraints
            )
            
            # Store in caches
            self._store_in_cache(cache_key, itinerary)
            
            return itinerary
            
        except Exception as e:
            # Fallback to mock provider
            self.logger.warning(f"Duffel API failed ({str(e)}), falling back to mock provider")
            mock_provider = MockPricingProvider(volatile=False)
            itinerary = await mock_provider.get_best_itinerary(
                origin, destination, depart_date, return_date, constraints
            )
            return itinerary
    
    async def _fetch_from_duffel_api(
        self,
        origin: str,
        destination: str,
        depart_date: date,
        return_date: date,
        constraints: dict
    ) -> Itinerary:
        """Fetch itinerary from Duffel API."""
        # Map travel class
        cabin_class_map = {
            "economy": "economy",
            "premium_economy": "premium_economy",
            "business": "business",
            "first": "first"
        }
        cabin_class = cabin_class_map.get(constraints.get("travel_class", "economy"), "economy")
        
        # Create offer request
        offer_request_data = {
            "slices": [
                {
                    "origin": origin,
                    "destination": destination,
                    "departure_date": depart_date.isoformat()
                },
                {
                    "origin": destination,
                    "destination": origin,
                    "departure_date": return_date.isoformat()
                }
            ],
            "passengers": [
                {
                    "type": "adult"
                }
            ],
            "cabin_class": cabin_class
        }
        
        # Create timeout (30 seconds)
        timeout = ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Create offer request
            async with session.post(
                f"{self.DUFFEL_API_BASE}/air/offer_requests",
                headers=self.headers,
                json={"data": offer_request_data}
            ) as resp:
                if resp.status != 201:
                    error_text = await resp.text()
                    raise ValueError(f"Duffel API error: {resp.status} - {error_text}")
                
                offer_request = await resp.json()
                offer_request_id = offer_request["data"]["id"]
            
            # Get offers
            async with session.get(
                f"{self.DUFFEL_API_BASE}/air/offers?offer_request_id={offer_request_id}",
                headers=self.headers
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise ValueError(f"Duffel API error: {resp.status} - {error_text}")
                
                offers_response = await resp.json()
                offers = offers_response.get("data", [])
            
            if not offers:
                raise ValueError("No offers returned from Duffel API")
            
            # Select best offer (lowest total_amount)
            best_offer = min(offers, key=lambda o: float(o.get("total_amount", "0")))
            
            # Extract itinerary details
            slices = best_offer.get("slices", [])
            if len(slices) < 2:
                raise ValueError("Invalid offer: missing return slice")
            
            outbound_slice = slices[0]
            return_slice = slices[1]
            
            # Get first segment of outbound
            outbound_segments = outbound_slice.get("segments", [])
            if not outbound_segments:
                raise ValueError("No segments in outbound slice")
            
            first_segment = outbound_segments[0]
            last_segment = outbound_segments[-1]
            
            # Calculate stops
            stops = len(outbound_segments) - 1
            
            # Parse times
            depart_time_str = first_segment.get("departing_at", "")
            arrive_time_str = last_segment.get("arriving_at", "")
            
            # Parse datetime strings
            depart_dt = datetime.fromisoformat(depart_time_str.replace("Z", "+00:00"))
            arrive_dt = datetime.fromisoformat(arrive_time_str.replace("Z", "+00:00"))
            
            depart_time = time(depart_dt.hour, depart_dt.minute)
            arrive_time = time(arrive_dt.hour, arrive_dt.minute)
            
            # Calculate travel minutes
            travel_minutes = int((arrive_dt - depart_dt).total_seconds() / 60)
            
            # Get airline
            airline = first_segment.get("marketing_carrier", {}).get("iata_code", "UNKNOWN")
            flight_number_raw = first_segment.get("marketing_carrier_flight_number")
            flight_number = f"{airline}{flight_number_raw}" if flight_number_raw else None
            
            # Get price (Duffel returns amount as string, e.g., "123.45")
            total_amount = best_offer.get("total_amount", "0")
            currency = best_offer.get("total_currency", "USD")
            # Convert to float (amount is already in major currency units)
            price = float(total_amount)
            
            # Generate Concur deep link
            concur_link = f"https://concur.example.com/book?origin={origin}&dest={destination}&date={depart_date}&offer_id={best_offer.get('id', '')}"
            
            # Build segment list from Duffel slices
            segments: list[ItinerarySegment] = []
            for slice_index, slice_data in enumerate(slices):
                leg = "outbound" if slice_index == 0 else "return"
                for seg_index, seg in enumerate(slice_data.get("segments", [])):
                    seg_origin = seg.get("origin", {}).get("iata_code", "")
                    seg_dest = seg.get("destination", {}).get("iata_code", "")
                    seg_depart = seg.get("departing_at", "")
                    seg_arrive = seg.get("arriving_at", "")
                    seg_depart_dt = datetime.fromisoformat(seg_depart.replace("Z", "+00:00")) if seg_depart else datetime.combine(depart_date, time(8, 0))
                    seg_arrive_dt = datetime.fromisoformat(seg_arrive.replace("Z", "+00:00")) if seg_arrive else seg_depart_dt + timedelta(minutes=90)
                    seg_airline = seg.get("marketing_carrier", {}).get("iata_code", "UNKNOWN")
                    seg_flight_raw = seg.get("marketing_carrier_flight_number")
                    seg_flight = f"{seg_airline}{seg_flight_raw}" if seg_flight_raw else None
                    duration_minutes = int((seg_arrive_dt - seg_depart_dt).total_seconds() / 60)
                    segments.append(
                        ItinerarySegment(
                            leg=leg,
                            segment_index=seg_index,
                            origin=seg_origin,
                            destination=seg_dest,
                            depart_time=seg_depart_dt.time(),
                            arrive_time=seg_arrive_dt.time(),
                            airline=seg_airline,
                            flight_number=seg_flight,
                            duration_minutes=max(duration_minutes, 0)
                        )
                    )

            return Itinerary(
                origin=origin,
                destination=destination,
                depart_date=depart_date,
                return_date=return_date,
                airline=airline,
                flight_number=flight_number,
                stops=stops,
                depart_time=depart_time,
                arrive_time=arrive_time,
                travel_minutes=travel_minutes,
                price=round(price, 2),
                concur_deep_link=concur_link,
                segments=segments
            )
    
    def _store_in_cache(self, cache_key: str, itinerary: Itinerary):
        """Store itinerary in both in-memory and SQLite caches."""
        # Cache in memory (LRU with maxsize handled by dict size limit)
        if len(self._in_memory_cache) > 1000:
            # Remove oldest entry (simple FIFO)
            oldest_key = next(iter(self._in_memory_cache))
            del self._in_memory_cache[oldest_key]
        self._in_memory_cache[cache_key] = itinerary
        
        # Cache in SQLite
        db = CacheSessionLocal()
        try:
            cache_entry = PriceCache(
                cache_key=cache_key,
                price=itinerary.price,
                airline=itinerary.airline,
                stops=itinerary.stops,
                travel_minutes=itinerary.travel_minutes
            )
            db.merge(cache_entry)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()


class ConcurProvider(PricingProvider):
    """Stub for Concur provider."""
    
    async def get_best_itinerary(
        self,
        origin: str,
        destination: str,
        depart_date: date,
        return_date: date,
        constraints: dict
    ) -> Itinerary:
        """TODO: Implement Concur integration."""
        raise NotImplementedError("ConcurProvider not yet implemented")
