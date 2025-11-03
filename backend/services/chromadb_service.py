"""
ChromaDB Service
Manages vector database for RAG with past evaluations
"""

import chromadb
import json
from typing import List, Dict, Optional
from models.schemas import EvaluationReport, Listing


class ChromaDBService:
    """Service for managing ChromaDB collections"""

    def __init__(self):
        # Initialize ChromaDB client with persistent storage (new API)
        self.client = chromadb.PersistentClient(path="./chroma_data")

        # Create or get collections
        self.evaluations_collection = self.client.get_or_create_collection(
            name="evaluations",
            metadata={"description": "Past property evaluations for RAG"}
        )

    def store_evaluation(
        self,
        listing: Listing,
        evaluation: EvaluationReport,
        user_preferences: dict
    ):
        """
        Store an evaluation in ChromaDB for future RAG retrieval

        Args:
            listing: The property listing
            evaluation: The evaluation report
            user_preferences: User's preferences used for this evaluation
        """
        # Create document text for embedding
        document_text = self._create_evaluation_document(listing, evaluation, user_preferences)

        # Create metadata
        metadata = {
            "listing_id": evaluation.listing_id,
            "address": listing.address,
            "price": listing.price,
            "bedrooms": listing.bedrooms,
            "bathrooms": listing.bathrooms,
            "sqft": listing.sqft,
            "final_score": evaluation.preference_match_score,
            "location": user_preferences.get("location", ""),
        }

        # Store in ChromaDB
        self.evaluations_collection.add(
            documents=[document_text],
            metadatas=[metadata],
            ids=[evaluation.listing_id]
        )

    def find_similar_evaluations(
        self,
        listing: Listing,
        user_preferences: dict,
        n_results: int = 5
    ) -> List[Dict]:
        """
        Find similar past evaluations using RAG

        Args:
            listing: The listing to find similar evaluations for
            user_preferences: User's current preferences
            n_results: Number of similar evaluations to retrieve

        Returns:
            List of similar evaluation documents
        """
        # Create query text
        query_text = self._create_query_text(listing, user_preferences)

        # Query ChromaDB
        results = self.evaluations_collection.query(
            query_texts=[query_text],
            n_results=n_results
        )

        # Format results
        similar_evaluations = []
        if results['documents'] and len(results['documents']) > 0:
            for i, doc in enumerate(results['documents'][0]):
                similar_evaluations.append({
                    "id": results['ids'][0][i],
                    "document": doc,
                    "metadata": results['metadatas'][0][i],
                    "distance": results['distances'][0][i] if 'distances' in results else None
                })

        return similar_evaluations

    def _create_evaluation_document(
        self,
        listing: Listing,
        evaluation: EvaluationReport,
        user_preferences: dict
    ) -> str:
        """Create a text document from an evaluation for embedding"""
        doc = f"""
Property Evaluation:
Address: {listing.address}
Type: {listing.property_type}
Price: ${listing.price}
Specs: {listing.bedrooms} bed, {listing.bathrooms} bath, {listing.sqft} sqft

User Preferences:
Location: {user_preferences.get('location', 'N/A')}
Budget: ${user_preferences.get('price_min', 0)} - ${user_preferences.get('price_max', 0)}
Size: {user_preferences.get('bedrooms_min', 0)}-{user_preferences.get('bedrooms_max', 0)} bedrooms

Evaluation Scores:
Preference Match: {evaluation.preference_match_score}/10
Crime Score: {evaluation.crime_score or 'N/A'}/10
School Score: {evaluation.school_score or 'N/A'}/10
Walkability: {evaluation.walkability_score or 'N/A'}/10

Strengths: {', '.join(evaluation.strengths)}
Concerns: {', '.join(evaluation.concerns)}

Notes: {evaluation.additional_notes or 'None'}
"""
        return doc.strip()

    def _create_query_text(self, listing: Listing, user_preferences: dict) -> str:
        """Create query text for finding similar evaluations"""
        query = f"""
Looking for evaluations of similar properties:
- Location: {user_preferences.get('location', listing.city)}
- Budget: ${user_preferences.get('price_min', 0)} - ${user_preferences.get('price_max', 0)}
- Property: {listing.bedrooms} bed, {listing.bathrooms} bath, {listing.sqft} sqft
- Price: ${listing.price}
- Type: {listing.property_type}
"""
        return query.strip()

    def get_collection_stats(self) -> Dict:
        """Get statistics about the evaluations collection"""
        return {
            "total_evaluations": self.evaluations_collection.count(),
            "collection_name": self.evaluations_collection.name
        }
