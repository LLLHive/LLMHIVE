"""Vision Agent for LLMHive.

This on-demand agent handles image analysis tasks using the multimodal ImageAnalyzer.
Provides comprehensive image understanding including:
- Image description and captioning
- OCR text extraction
- Object detection
- Landmark identification
- Visual question answering

Integrates with OpenAI Vision, Anthropic Vision, and local OCR providers.
"""
from __future__ import annotations

import base64
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from .base import BaseAgent, AgentConfig, AgentResult, AgentTask, AgentType, AgentPriority

logger = logging.getLogger(__name__)


# ============================================================
# Vision Analysis Data Classes
# ============================================================

@dataclass
class VisionAnalysisRequest:
    """Request for vision analysis."""
    image_source: str  # URL, file path, or base64
    source_type: str = "auto"  # "url", "path", "base64", "auto"
    analysis_types: List[str] = field(default_factory=lambda: ["describe"])
    question: Optional[str] = None
    max_tokens: int = 500


@dataclass
class VisionAnalysisResult:
    """Result of vision analysis."""
    description: str
    extracted_text: Optional[str] = None
    detected_objects: List[str] = field(default_factory=list)
    landmarks: List[str] = field(default_factory=list)
    labels: List[str] = field(default_factory=list)
    provider_used: Optional[str] = None
    confidence: float = 0.0
    error: Optional[str] = None
    processing_time_ms: int = 0


# ============================================================
# Vision Agent Implementation
# ============================================================

class VisionAgent(BaseAgent):
    """Agent that handles image analysis tasks.
    
    Responsibilities:
    - Analyze uploaded images using multimodal LLMs
    - Extract text via OCR
    - Generate image descriptions/captions
    - Detect objects and landmarks
    - Answer visual questions (VQA)
    
    Task Types:
    - analyze_image: Full image analysis
    - extract_text: OCR text extraction only
    - describe_image: Generate image caption/description
    - answer_question: Visual question answering
    - detect_objects: Object detection
    
    Supported Image Sources:
    - URLs (http/https)
    - File paths (local files)
    - Base64 encoded images
    """
    
    # Analysis type mapping
    ANALYSIS_TYPES = {
        "describe": "describe",
        "ocr": "ocr",
        "objects": "objects",
        "landmarks": "landmarks",
        "labels": "labels",
        "text": "ocr",  # Alias
        "caption": "describe",  # Alias
    }
    
    def __init__(self, config: Optional[AgentConfig] = None, blackboard: Optional[Any] = None):
        if config is None:
            config = AgentConfig(
                name="vision_agent",
                agent_type=AgentType.ON_DEMAND,
                priority=AgentPriority.HIGH,
                max_tokens_per_run=5000,
                allowed_tools=["ocr", "image_captioner", "gpt4v", "claude_vision"],
                memory_namespace="vision",
            )
        super().__init__(config)
        self.blackboard = blackboard
        self._analyzer = None
        self._analysis_history: List[Dict[str, Any]] = []
    
    def _get_analyzer(self):
        """Lazy load the ImageAnalyzer to avoid import issues."""
        if self._analyzer is None:
            try:
                from ..multimodal.image_analyzer import ImageAnalyzer
                self._analyzer = ImageAnalyzer()
                logger.info("ImageAnalyzer initialized for VisionAgent")
            except ImportError as e:
                logger.error("Failed to import ImageAnalyzer: %s", e)
                self._analyzer = None
        return self._analyzer
    
    async def execute(self, task: Optional[AgentTask] = None) -> AgentResult:
        """Execute vision analysis task.
        
        Args:
            task: AgentTask with task_type and payload containing image info
            
        Returns:
            AgentResult with vision analysis output
        """
        start_time = datetime.now()
        
        if not task:
            return AgentResult(
                success=False,
                error="No task provided. Provide task with image_source in payload.",
            )
        
        task_type = task.task_type
        payload = task.payload
        
        try:
            if task_type == "analyze_image":
                return await self._analyze_image(payload, start_time)
            
            elif task_type == "extract_text":
                return await self._extract_text(payload, start_time)
            
            elif task_type == "describe_image":
                return await self._describe_image(payload, start_time)
            
            elif task_type == "answer_question":
                return await self._answer_question(payload, start_time)
            
            elif task_type == "detect_objects":
                return await self._detect_objects(payload, start_time)
            
            elif task_type == "get_capabilities":
                return AgentResult(
                    success=True,
                    output=self.get_capabilities(),
                )
            
            elif task_type == "get_history":
                return AgentResult(
                    success=True,
                    output={"history": self._analysis_history[-10:]},  # Last 10
                )
            
            else:
                return AgentResult(
                    success=False,
                    error=f"Unknown task type: {task_type}. Supported: analyze_image, extract_text, describe_image, answer_question, detect_objects",
                )
                
        except Exception as e:
            logger.error("Vision Agent execution failed: %s", e, exc_info=True)
            return AgentResult(
                success=False,
                error=f"Vision analysis failed: {str(e)}",
            )
    
    async def _analyze_image(
        self,
        payload: Dict[str, Any],
        start_time: datetime,
    ) -> AgentResult:
        """Perform comprehensive image analysis."""
        image_source = payload.get("image_source") or payload.get("image") or payload.get("url")
        
        if not image_source:
            return AgentResult(
                success=False,
                error="No image_source provided in payload",
            )
        
        analyzer = self._get_analyzer()
        if analyzer is None:
            return await self._fallback_analysis(image_source, payload, start_time)
        
        # Parse analysis types
        analysis_types = payload.get("analysis_types", ["describe", "ocr", "objects"])
        question = payload.get("question")
        max_tokens = payload.get("max_tokens", 500)
        
        # Import and convert analysis types
        try:
            from ..multimodal.image_analyzer import AnalysisType
            
            types = []
            for atype in analysis_types:
                mapped = self.ANALYSIS_TYPES.get(atype.lower(), atype.lower())
                try:
                    types.append(AnalysisType(mapped))
                except ValueError:
                    logger.warning("Unknown analysis type: %s", atype)
            
            if not types:
                types = [AnalysisType.DESCRIBE]
            
            # Perform analysis
            result = await analyzer.analyze(
                image_source,
                analysis_types=types,
                question=question,
                max_tokens=max_tokens,
            )
            
            # Calculate processing time
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # Build output
            output = VisionAnalysisResult(
                description=result.description,
                extracted_text=result.all_text if result.extracted_text else None,
                detected_objects=[obj.name for obj in result.detected_objects],
                landmarks=result.landmarks,
                labels=result.labels,
                provider_used=result.provider_used,
                confidence=0.9 if not result.error else 0.0,
                error=result.error,
                processing_time_ms=processing_time,
            )
            
            # Track analysis
            self._track_analysis(image_source, output)
            
            # Update blackboard if available
            if self.blackboard and hasattr(self.blackboard, "write"):
                self.blackboard.write("last_vision_analysis", {
                    "description": output.description,
                    "extracted_text": output.extracted_text,
                    "objects": output.detected_objects,
                    "timestamp": datetime.now().isoformat(),
                })
            
            return AgentResult(
                success=not result.error,
                output={
                    "description": output.description,
                    "extracted_text": output.extracted_text,
                    "detected_objects": output.detected_objects,
                    "landmarks": output.landmarks,
                    "labels": output.labels,
                    "provider": output.provider_used,
                    "confidence": output.confidence,
                    "processing_time_ms": output.processing_time_ms,
                    "summary": result.summary,
                },
                error=result.error,
                metadata={
                    "agent": "vision_agent",
                    "task_type": "analyze_image",
                    "processing_time_ms": processing_time,
                },
            )
            
        except ImportError:
            return await self._fallback_analysis(image_source, payload, start_time)
    
    async def _extract_text(
        self,
        payload: Dict[str, Any],
        start_time: datetime,
    ) -> AgentResult:
        """Extract text from image using OCR."""
        payload["analysis_types"] = ["ocr"]
        result = await self._analyze_image(payload, start_time)
        
        if result.success and result.output:
            # Simplify output for OCR-only request
            result.output = {
                "extracted_text": result.output.get("extracted_text", ""),
                "confidence": result.output.get("confidence", 0),
                "provider": result.output.get("provider"),
            }
        
        return result
    
    async def _describe_image(
        self,
        payload: Dict[str, Any],
        start_time: datetime,
    ) -> AgentResult:
        """Generate image description/caption."""
        payload["analysis_types"] = ["describe"]
        result = await self._analyze_image(payload, start_time)
        
        if result.success and result.output:
            result.output = {
                "description": result.output.get("description", ""),
                "confidence": result.output.get("confidence", 0),
                "provider": result.output.get("provider"),
            }
        
        return result
    
    async def _answer_question(
        self,
        payload: Dict[str, Any],
        start_time: datetime,
    ) -> AgentResult:
        """Answer a question about an image (VQA)."""
        question = payload.get("question")
        if not question:
            return AgentResult(
                success=False,
                error="No question provided for visual QA",
            )
        
        payload["analysis_types"] = ["describe"]
        return await self._analyze_image(payload, start_time)
    
    async def _detect_objects(
        self,
        payload: Dict[str, Any],
        start_time: datetime,
    ) -> AgentResult:
        """Detect objects in image."""
        payload["analysis_types"] = ["objects", "labels"]
        result = await self._analyze_image(payload, start_time)
        
        if result.success and result.output:
            result.output = {
                "detected_objects": result.output.get("detected_objects", []),
                "labels": result.output.get("labels", []),
                "confidence": result.output.get("confidence", 0),
                "provider": result.output.get("provider"),
            }
        
        return result
    
    async def _fallback_analysis(
        self,
        image_source: str,
        payload: Dict[str, Any],
        start_time: datetime,
    ) -> AgentResult:
        """Fallback when ImageAnalyzer is not available."""
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Determine source type for helpful error message
        source_type = "unknown"
        if image_source.startswith(("http://", "https://")):
            source_type = "URL"
        elif Path(image_source).exists() if not image_source.startswith("data:") else False:
            source_type = "file"
        elif len(image_source) > 1000:
            source_type = "base64"
        
        return AgentResult(
            success=False,
            output={
                "description": "Image analysis unavailable - no vision providers configured",
                "source_type": source_type,
                "image_source": image_source[:100] + "..." if len(image_source) > 100 else image_source,
            },
            error="ImageAnalyzer not available. Configure OPENAI_API_KEY or ANTHROPIC_API_KEY for vision capabilities.",
            metadata={
                "agent": "vision_agent",
                "task_type": "fallback",
                "processing_time_ms": processing_time,
            },
        )
    
    def _track_analysis(self, image_source: str, result: VisionAnalysisResult) -> None:
        """Track analysis for history and metrics."""
        self._analysis_history.append({
            "timestamp": datetime.now().isoformat(),
            "source_preview": image_source[:50] + "..." if len(image_source) > 50 else image_source,
            "provider": result.provider_used,
            "has_text": bool(result.extracted_text),
            "object_count": len(result.detected_objects),
            "success": not result.error,
            "processing_time_ms": result.processing_time_ms,
        })
        
        # Keep only last 100 entries
        if len(self._analysis_history) > 100:
            self._analysis_history = self._analysis_history[-100:]
    
    def get_capabilities(self) -> Dict[str, Any]:
        """Get agent capabilities description."""
        analyzer = self._get_analyzer()
        
        providers_available = []
        if analyzer and hasattr(analyzer, "_available_providers"):
            providers_available = [p.value for p in analyzer._available_providers]
        
        return {
            "name": "Vision Agent",
            "type": "on_demand",
            "purpose": "Analyze images and answer visual questions",
            "task_types": [
                "analyze_image",
                "extract_text",
                "describe_image",
                "answer_question",
                "detect_objects",
                "get_capabilities",
                "get_history",
            ],
            "analysis_types": list(self.ANALYSIS_TYPES.keys()),
            "supports": [
                "OCR text extraction",
                "Image captioning",
                "Object detection",
                "Landmark identification",
                "Visual question answering",
            ],
            "providers_available": providers_available,
            "image_sources": ["URL", "file path", "base64"],
            "max_image_size": "20MB",
            "supported_formats": ["jpg", "jpeg", "png", "gif", "webp", "bmp"],
        }
