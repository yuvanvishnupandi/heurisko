"""
Pydantic models for the fact-checking system.
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import List, Dict, Any, Optional, Annotated, Literal, Union
from typing_extensions import TypedDict
from datetime import datetime
from langgraph.graph import add_messages

# Basic types
EntityType = Dict[str, Any]
SourceType = Dict[str, Any]
EvidenceType = Dict[str, Any]

class AtomicClaim(BaseModel):
    """An atomic verifiable unit extracted from a complex claim."""
    id: str
    statement: str
    entities: List[str] = Field(default_factory=list)
    time_references: Optional[List[str]] = Field(default_factory=list)
    location_references: Optional[List[str]] = Field(default_factory=list)
    numeric_values: Optional[List[str]] = Field(default_factory=list)
    importance: float = Field(default=1.0, ge=0.0, le=1.0, description="Relative importance of this atomic claim")

class Evidence(BaseModel):
    """Evidence collected to verify a claim."""
    id: str
    source: str = Field(description="Source of the evidence (e.g., 'web', 'wikidata', 'news')")
    url: Optional[str] = None
    content: str
    retrieval_date: datetime = Field(default_factory=datetime.now)
    credibility_score: float = Field(default=0.5, ge=0.0, le=1.0)
    relevance_score: float = Field(default=0.5, ge=0.0, le=1.0)

class EvidenceCollection(BaseModel):
    """Collection of evidence for a specific claim."""
    claim_id: str
    search_results: List[Evidence] = Field(default_factory=list)
    knowledge_base: List[Evidence] = Field(default_factory=list)
    news_sources: List[Evidence] = Field(default_factory=list)

class VerificationResult(BaseModel):
    """Result of claim verification by a single agent."""
    agent_id: str
    verdict: Literal["TRUE", "FALSE", "PARTIALLY_TRUE", "UNVERIFIABLE", "NEEDS_CONTEXT"]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    evidence_assessment: Dict[str, float] = Field(description="Assessment of each evidence piece")
    reasoning_difficulty: float = Field(default=0.0, ge=0.0, le=1.0)
    claim_ambiguity: float = Field(default=0.0, ge=0.0, le=1.0)

class ClaimVerificationResults(BaseModel):
    """Compilation of verification results from multiple agents for a single claim."""
    claim_id: str
    primary: VerificationResult
    cross: Optional[VerificationResult] = None
    historical: Optional[VerificationResult] = None
    reconciled: Optional[VerificationResult] = None

class AtomicClaimList(BaseModel):
    """A container for a list of atomic claims."""
    claims: List[AtomicClaim]

class FinalVerdict(BaseModel):
    """Final verdict for a claim with confidence scoring and evidence summary."""
    claim_id: str
    claim_text: str
    verdict: Literal["TRUE", "FALSE", "PARTIALLY_TRUE", "UNVERIFIABLE", "NEEDS_CONTEXT"]
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    evidence_summary: str
    sources_used: List[Dict[str, Any]] = Field(default_factory=list, description="Sources used to verify this claim")
    verification_date: datetime = Field(default_factory=datetime.now)

class ComprehensiveVerdict(BaseModel):
    """Comprehensive verdict for the original input claim, synthesizing atomic claim verdicts."""
    original_claim: str
    atomic_verdicts: Dict[str, FinalVerdict]
    overall_verdict: Literal["TRUE", "FALSE", "PARTIALLY_TRUE", "UNVERIFIABLE", "NEEDS_CONTEXT"]
    overall_confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    summary: str
    process_steps: List[Dict[str, Any]] = Field(default_factory=list, description="Steps taken during the fact-checking process")
    sources_used: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict, description="Sources used for each claim")
    verification_date: datetime = Field(default_factory=datetime.now)

# LangGraph state for workflow orchestration
class FactCheckState(BaseModel):
    """State model for the fact-checking workflow."""
    input_claim: str
    decomposed_claims: List[AtomicClaim] = Field(default_factory=list)
    evidence_collections: Dict[str, EvidenceCollection] = Field(default_factory=dict)
    verification_results: Dict[str, ClaimVerificationResults] = Field(default_factory=dict)
    confidence_scores: Dict[str, float] = Field(default_factory=dict)
    final_verdict: Optional[ComprehensiveVerdict] = None
    messages: Annotated[List, add_messages] = Field(default_factory=list)
    intermediate_steps: List[Dict[str, Any]] = Field(default_factory=list, description="Track all intermediate steps in the fact-checking process")
    sources_used: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict, description="Track all sources used for each claim")

class Source(BaseModel):
    """Represents a single source of information used in the research."""
    url: Optional[HttpUrl] = Field(None, description="The URL of the source.")
    title: Optional[str] = Field(None, description="The title of the source page or document.")
    snippet: Optional[str] = Field(None, description="A relevant excerpt or summary from the source.")
    tool_used: Optional[str] = Field(None, description="The tool used to retrieve this source (e.g., 'tavily_search', 'news_search').")
    retrieved_at: datetime = Field(default_factory=datetime.now, description="Timestamp when the source was retrieved.")

class ResearchReportSection(BaseModel):
    """Represents a section within the final research report."""
    heading: str = Field(..., description="The heading or title of this report section.")
    content: str = Field(..., description="The detailed content for this section, synthesized from sources.")
    relevant_source_indices: Optional[List[int]] = Field(None, description="Indices referring to the main 'sources' list relevant to this section.")

class ResearchReport(BaseModel):
    """Defines the structure for the final research report."""
    query: str = Field(..., description="The original research query submitted by the user.")
    summary: str = Field(..., description="A concise executive summary of the key findings.")
    sections: List[ResearchReportSection] = Field(..., description="Detailed sections covering different aspects of the research.")
    # We keep sources at the top level for easier reference by index
    sources: List[Source] = Field(..., description="A list of all unique sources consulted during the research.")
    potential_biases: Optional[str] = Field(None, description="A brief note on potential biases or limitations found during research (e.g., lack of diverse sources, conflicting information).")
    report_generated_at: datetime = Field(default_factory=datetime.now, description="Timestamp when the report was generated.")

class ResearchRequest(BaseModel):
    """Request model for initiating research."""
    query: str = Field(..., description="The research query.")
    language: Optional[str] = Field("en", description="Optional language code for the research (e.g., 'en', 'es').")
    chat_history: List[Dict[str, str]] = Field(default_factory=list, description="Optional history of previous chat messages in the thread.")
    history_id: Optional[int] = Field(None, description="The ID of the chat history to append to.")

class IntermediateStep(BaseModel):
    """Represents an intermediate step taken by the agent during research."""
    thought: Optional[str] = Field(None, description="The agent's reasoning or thought process for this step.")
    action: Optional[str] = Field(None, description="The tool or action taken (e.g., 'tavily_search', 'scrape_webpages').")
    action_input: Optional[Union[Dict[str, Any], str]] = Field(None, description="The input provided to the tool/action.")
    observation: Optional[str] = Field(None, description="The result or observation obtained from the tool/action.")
    timestamp: datetime = Field(default_factory=datetime.now)

class ResearchProgress(BaseModel):
    """Used to stream progress updates back to the client (optional)."""
    status: str = Field(..., description="Current status message (e.g., 'Analyzing query', 'Searching web', 'Synthesizing report').")
    intermediate_steps: List[IntermediateStep] = Field(default_factory=list, description="Log of steps taken so far.")
    partial_report: Optional[ResearchReport] = Field(None, description="A partial or draft report if available.")

# You might want to keep ErrorResponse or define a new one
class ErrorResponse(BaseModel):
    """Standard error response format."""
    error: str = Field(..., description="Description of the error.")
    details: Optional[str] = Field(None, description="Optional further details about the error.")


# Example definition if ToolInput is needed by tools.py or agent.py
class ToolInput(BaseModel):
    """Generic input model for tools (adjust as needed)."""
    query: Optional[str] = None
    url: Optional[HttpUrl] = None
    urls: Optional[List[HttpUrl]] = None
    entity: Optional[str] = None
    prop_id: Optional[str] = None
    # Add other common tool inputs
    # You might prefer more specific input models per tool

# Added from models.py
class GeminiParsedOutput(BaseModel):
    """Model for the structured output expected from parsing the Gemini+GoogleSearch result."""
    summary: str = Field(..., description="Concise summary of the findings related to the query, based on the search.")
    key_facts: List[str] = Field(default_factory=list, description="List of key facts or pieces of information identified in the search results.")
    sources: List[str] = Field(default_factory=list, description="List of source URLs mentioned or used in the Gemini output.")
    source_tool: str = Field(default="gemini_google_search_tool", description="Indicates the source tool.") 


