#!/usr/bin/env python3
"""
CleanSlate Phase 4 - AI/Media Optimization
Advanced file analysis with AI-powered content detection and media optimization.
"""

import os
import sys
import json
import hashlib
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import cv2
import numpy as np
from PIL import Image, ImageEnhance
import imagehash
from sklearn.cluster import DBSCAN
from sklearn.feature_extraction.text import TfidfVectorizer
import jieba
import re

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from cleanslate_core import (
    load_config, save_config, run_scan,
    REPORT_FILE, REPORT_HTML_FILE
)

class AIAnalyzer:
    """AI-powered file analysis and content detection."""
    
    def __init__(self):
        """Initialize AI analyzer with models and settings."""
        self.content_cache = {}
        self.similarity_threshold = 0.85
        self.cluster_eps = 0.3
        self.min_samples = 2
        
    def analyze_file_content(self, file_path: str) -> Dict[str, Any]:
        """Analyze file content and extract features."""
        if file_path in self.content_cache:
            return self.content_cache[file_path]
            
        analysis = {
            'file_type': self._detect_file_type(file_path),
            'content_hash': self._generate_content_hash(file_path),
            'text_features': None,
            'image_features': None,
            'audio_features': None,
            'video_features': None,
            'metadata': self._extract_metadata(file_path),
            'ai_score': 0.0
        }
        
        # Text analysis
        if analysis['file_type']['category'] == 'text':
            analysis['text_features'] = self._analyze_text_content(file_path)
            
        # Image analysis
        elif analysis['file_type']['category'] == 'image':
            analysis['image_features'] = self._analyze_image_content(file_path)
            
        # Audio analysis
        elif analysis['file_type']['category'] == 'audio':
            analysis['audio_features'] = self._analyze_audio_content(file_path)
            
        # Video analysis
        elif analysis['file_type']['category'] == 'video':
            analysis['video_features'] = self._analyze_video_content(file_path)
            
        # Calculate AI score
        analysis['ai_score'] = self._calculate_ai_score(analysis)
        
        self.content_cache[file_path] = analysis
        return analysis
    
    def _detect_file_type(self, file_path: str) -> Dict[str, str]:
        """Detect file type and category."""
        mime_type, _ = mimetypes.guess_type(file_path)
        
        if mime_type:
            if mime_type.startswith('text/'):
                category = 'text'
            elif mime_type.startswith('image/'):
                category = 'image'
            elif mime_type.startswith('audio/'):
                category = 'audio'
            elif mime_type.startswith('video/'):
                category = 'video'
            else:
                category = 'other'
        else:
            # Fallback based on extension
            ext = Path(file_path).suffix.lower()
            if ext in ['.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml']:
                category = 'text'
            elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']:
                category = 'image'
            elif ext in ['.mp3', '.wav', '.flac', '.aac', '.ogg']:
                category = 'audio'
            elif ext in ['.mp4', '.avi', '.mov', '.mkv', '.wmv']:
                category = 'video'
            else:
                category = 'other'
        
        return {
            'mime_type': mime_type or 'unknown',
            'category': category,
            'extension': Path(file_path).suffix.lower()
        }
    
    def _generate_content_hash(self, file_path: str) -> str:
        """Generate content-based hash."""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                return hashlib.sha256(content).hexdigest()
        except Exception:
            return ""
    
    def _extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract file metadata."""
        stat = os.stat(file_path)
        return {
            'size': stat.st_size,
            'created': datetime.fromtimestamp(stat.st_ctime),
            'modified': datetime.fromtimestamp(stat.st_mtime),
            'accessed': datetime.fromtimestamp(stat.st_atime)
        }
    
    def _analyze_text_content(self, file_path: str) -> Dict[str, Any]:
        """Analyze text content and extract features."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Basic text analysis
            words = re.findall(r'\w+', content.lower())
            sentences = re.split(r'[.!?]+', content)
            
            # Language detection (simplified)
            chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
            english_chars = len(re.findall(r'[a-zA-Z]', content))
            
            if chinese_chars > english_chars:
                language = 'chinese'
                # Use jieba for Chinese text
                word_tokens = list(jieba.cut(content))
            else:
                language = 'english'
                word_tokens = words
            
            return {
                'language': language,
                'word_count': len(word_tokens),
                'sentence_count': len([s for s in sentences if s.strip()]),
                'avg_sentence_length': len(word_tokens) / max(len([s for s in sentences if s.strip()]), 1),
                'unique_words': len(set(word_tokens)),
                'vocabulary_diversity': len(set(word_tokens)) / max(len(word_tokens), 1),
                'content_preview': content[:500] + '...' if len(content) > 500 else content
            }
        except Exception:
            return {}
    
    def _analyze_image_content(self, file_path: str) -> Dict[str, Any]:
        """Analyze image content and extract features."""
        try:
            image = cv2.imread(file_path)
            if image is None:
                return {}
            
            # Basic image features
            height, width = image.shape[:2]
            aspect_ratio = width / height if height > 0 else 0
            
            # Color analysis
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            avg_saturation = np.mean(hsv[:, :, 1])
            avg_value = np.mean(hsv[:, :, 2])
            
            # Edge detection for complexity
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges > 0) / (height * width)
            
            # Blur detection
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # Perceptual hash
            pil_image = Image.open(file_path)
            phash = str(imagehash.phash(pil_image))
            
            return {
                'dimensions': (width, height),
                'aspect_ratio': aspect_ratio,
                'file_size_mb': os.path.getsize(file_path) / (1024 * 1024),
                'avg_saturation': float(avg_saturation),
                'avg_brightness': float(avg_value),
                'edge_density': float(edge_density),
                'blur_score': float(laplacian_var),
                'perceptual_hash': phash,
                'is_blurry': laplacian_var < 100,
                'is_dark': avg_value < 100,
                'is_saturated': avg_saturation > 150
            }
        except Exception:
            return {}
    
    def _analyze_audio_content(self, file_path: str) -> Dict[str, Any]:
        """Analyze audio content and extract features."""
        try:
            # Basic audio analysis (simplified)
            file_size = os.path.getsize(file_path)
            duration_estimate = file_size / (128 * 1024)  # Rough estimate for MP3
            
            return {
                'file_size_mb': file_size / (1024 * 1024),
                'estimated_duration_min': duration_estimate / 60,
                'bitrate_estimate': 128,  # Assume 128kbps
                'format': Path(file_path).suffix.lower()
            }
        except Exception:
            return {}
    
    def _analyze_video_content(self, file_path: str) -> Dict[str, Any]:
        """Analyze video content and extract features."""
        try:
            cap = cv2.VideoCapture(file_path)
            if not cap.isOpened():
                return {}
            
            # Basic video features
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            duration = frame_count / fps if fps > 0 else 0
            
            cap.release()
            
            return {
                'dimensions': (width, height),
                'fps': fps,
                'frame_count': frame_count,
                'duration_seconds': duration,
                'duration_minutes': duration / 60,
                'file_size_mb': os.path.getsize(file_path) / (1024 * 1024),
                'aspect_ratio': width / height if height > 0 else 0
            }
        except Exception:
            return {}
    
    def _calculate_ai_score(self, analysis: Dict[str, Any]) -> float:
        """Calculate AI-based importance score."""
        score = 0.0
        
        # File type scoring
        file_type = analysis['file_type']['category']
        if file_type == 'image':
            score += 0.3
        elif file_type == 'video':
            score += 0.4
        elif file_type == 'audio':
            score += 0.2
        elif file_type == 'text':
            score += 0.1
        
        # Content quality scoring
        if analysis['image_features']:
            img_feat = analysis['image_features']
            if not img_feat.get('is_blurry', True):
                score += 0.2
            if not img_feat.get('is_dark', True):
                score += 0.1
            if img_feat.get('edge_density', 0) > 0.1:
                score += 0.1
        
        if analysis['text_features']:
            text_feat = analysis['text_features']
            if text_feat.get('vocabulary_diversity', 0) > 0.5:
                score += 0.2
            if text_feat.get('word_count', 0) > 100:
                score += 0.1
        
        # Size scoring (prefer medium-sized files)
        metadata = analysis['metadata']
        size_mb = metadata['size'] / (1024 * 1024)
        if 0.1 < size_mb < 50:
            score += 0.1
        elif size_mb > 100:
            score -= 0.1
        
        return min(score, 1.0)
    
    def find_content_duplicates(self, files: List[str]) -> Dict[str, List[str]]:
        """Find content-based duplicates using AI analysis."""
        print("🔍 AI: Analyzing file content for intelligent duplicate detection...")
        
        # Analyze all files
        analyses = {}
        for file_path in files:
            analyses[file_path] = self.analyze_file_content(file_path)
        
        # Group by content hash (exact duplicates)
        hash_groups = {}
        for file_path, analysis in analyses.items():
            content_hash = analysis['content_hash']
            if content_hash:
                if content_hash not in hash_groups:
                    hash_groups[content_hash] = []
                hash_groups[content_hash].append(file_path)
        
        # Find near-duplicates by category
        near_duplicates = {}
        
        # Image near-duplicates
        image_files = [f for f in files if analyses[f]['file_type']['category'] == 'image']
        if len(image_files) > 1:
            image_duplicates = self._find_image_near_duplicates(image_files, analyses)
            near_duplicates.update(image_duplicates)
        
        # Text near-duplicates
        text_files = [f for f in files if analyses[f]['file_type']['category'] == 'text']
        if len(text_files) > 1:
            text_duplicates = self._find_text_near_duplicates(text_files, analyses)
            near_duplicates.update(text_duplicates)
        
        # Combine exact and near duplicates
        all_duplicates = {}
        group_id = 1
        
        # Add exact duplicates
        for hash_val, file_list in hash_groups.items():
            if len(file_list) > 1:
                all_duplicates[f"exact_group_{group_id}"] = file_list
                group_id += 1
        
        # Add near duplicates
        for group_name, file_list in near_duplicates.items():
            all_duplicates[f"near_{group_name}"] = file_list
        
        return all_duplicates
    
    def _find_image_near_duplicates(self, image_files: List[str], analyses: Dict[str, Any]) -> Dict[str, List[str]]:
        """Find near-duplicate images using perceptual hashing."""
        hash_groups = {}
        
        for file_path in image_files:
            analysis = analyses[file_path]
            if 'image_features' in analysis and 'perceptual_hash' in analysis['image_features']:
                phash = analysis['image_features']['perceptual_hash']
                
                # Group by perceptual hash (very similar images)
                if phash not in hash_groups:
                    hash_groups[phash] = []
                hash_groups[phash].append(file_path)
        
        # Return groups with multiple files
        return {f"image_group_{i}": files for i, (_, files) in enumerate(hash_groups.items()) if len(files) > 1}
    
    def _find_text_near_duplicates(self, text_files: List[str], analyses: Dict[str, Any]) -> Dict[str, List[str]]:
        """Find near-duplicate text files using TF-IDF similarity."""
        if len(text_files) < 2:
            return {}
        
        # Extract text content
        texts = []
        valid_files = []
        
        for file_path in text_files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if len(content.strip()) > 50:  # Only consider files with substantial content
                        texts.append(content)
                        valid_files.append(file_path)
            except Exception:
                continue
        
        if len(texts) < 2:
            return {}
        
        # Use TF-IDF for similarity
        try:
            vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
            tfidf_matrix = vectorizer.fit_transform(texts)
            
            # Calculate cosine similarity
            from sklearn.metrics.pairwise import cosine_similarity
            similarity_matrix = cosine_similarity(tfidf_matrix)
            
            # Group similar files
            groups = []
            used_indices = set()
            
            for i in range(len(similarity_matrix)):
                if i in used_indices:
                    continue
                
                similar_files = [valid_files[i]]
                used_indices.add(i)
                
                for j in range(i + 1, len(similarity_matrix)):
                    if j not in used_indices and similarity_matrix[i][j] > self.similarity_threshold:
                        similar_files.append(valid_files[j])
                        used_indices.add(j)
                
                if len(similar_files) > 1:
                    groups.append(similar_files)
            
            return {f"text_group_{i}": group for i, group in enumerate(groups)}
            
        except Exception:
            return {}


class MediaOptimizer:
    """Media file optimization and enhancement."""
    
    def __init__(self):
        """Initialize media optimizer."""
        self.optimization_settings = {
            'image_quality': 85,
            'image_max_width': 1920,
            'image_max_height': 1080,
            'video_bitrate': '2M',
            'audio_bitrate': '128k'
        }
    
    def optimize_image(self, input_path: str, output_path: str) -> bool:
        """Optimize image file."""
        try:
            with Image.open(input_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Resize if too large
                width, height = img.size
                if width > self.optimization_settings['image_max_width'] or height > self.optimization_settings['image_max_height']:
                    img.thumbnail((self.optimization_settings['image_max_width'], self.optimization_settings['image_max_height']), Image.Resampling.LANCZOS)
                
                # Save with optimization
                img.save(output_path, 'JPEG', quality=self.optimization_settings['image_quality'], optimize=True)
                
                return True
        except Exception as e:
            print(f"Error optimizing image {input_path}: {e}")
            return False
    
    def enhance_image(self, input_path: str, output_path: str) -> bool:
        """Enhance image quality."""
        try:
            with Image.open(input_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Enhance brightness and contrast
                enhancer = ImageEnhance.Brightness(img)
                img = enhancer.enhance(1.1)  # Slightly brighter
                
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(1.2)  # More contrast
                
                enhancer = ImageEnhance.Sharpness(img)
                img = enhancer.enhance(1.1)  # Slightly sharper
                
                # Save enhanced image
                img.save(output_path, 'JPEG', quality=90, optimize=True)
                
                return True
        except Exception as e:
            print(f"Error enhancing image {input_path}: {e}")
            return False
    
    def generate_thumbnail(self, input_path: str, output_path: str, size: Tuple[int, int] = (200, 200)) -> bool:
        """Generate thumbnail for image or video."""
        try:
            if input_path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                # Video thumbnail
                cap = cv2.VideoCapture(input_path)
                ret, frame = cap.read()
                cap.release()
                
                if ret:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(frame)
                    img.thumbnail(size, Image.Resampling.LANCZOS)
                    img.save(output_path, 'JPEG', quality=85)
                    return True
            else:
                # Image thumbnail
                with Image.open(input_path) as img:
                    if img.mode in ('RGBA', 'LA', 'P'):
                        img = img.convert('RGB')
                    img.thumbnail(size, Image.Resampling.LANCZOS)
                    img.save(output_path, 'JPEG', quality=85)
                    return True
                    
        except Exception as e:
            print(f"Error generating thumbnail for {input_path}: {e}")
            return False


class AdvancedReporter:
    """Advanced reporting with AI insights and recommendations."""
    
    def __init__(self, ai_analyzer: AIAnalyzer):
        """Initialize advanced reporter."""
        self.ai_analyzer = ai_analyzer
        self.report_data = {}
    
    def generate_ai_report(self, scan_results: Dict, analyses: Dict[str, Any]) -> str:
        """Generate AI-enhanced report with insights and recommendations."""
        report = []
        report.append("🧠 CleanSlate Phase 4 - AI Analysis Report")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # AI Insights
        insights = self._generate_ai_insights(scan_results, analyses)
        report.append("🤖 AI INSIGHTS")
        report.append("-" * 40)
        for insight in insights:
            report.append(f"• {insight}")
        report.append("")
        
        # Content Analysis
        content_analysis = self._analyze_content_distribution(analyses)
        report.append("📊 CONTENT ANALYSIS")
        report.append("-" * 40)
        for category, stats in content_analysis.items():
            report.append(f"{category.upper()}:")
            report.append(f"  - Files: {stats['count']}")
            report.append(f"  - Total Size: {stats['total_size_mb']:.2f} MB")
            report.append(f"  - Avg Quality Score: {stats['avg_ai_score']:.2f}")
        report.append("")
        
        # Recommendations
        recommendations = self._generate_recommendations(scan_results, analyses)
        report.append("💡 RECOMMENDATIONS")
        report.append("-" * 40)
        for i, rec in enumerate(recommendations, 1):
            report.append(f"{i}. {rec}")
        report.append("")
        
        # Detailed Findings
        report.append("🔍 DETAILED FINDINGS")
        report.append("-" * 40)
        
        # High-value files
        high_value = self._find_high_value_files(analyses)
        if high_value:
            report.append("High-Value Files (AI Score > 0.7):")
            for file_path, score in high_value:
                report.append(f"  - {file_path} (Score: {score:.2f})")
            report.append("")
        
        # Low-quality files
        low_quality = self._find_low_quality_files(analyses)
        if low_quality:
            report.append("Low-Quality Files (Consider removal):")
            for file_path, reason in low_quality:
                report.append(f"  - {file_path} ({reason})")
            report.append("")
        
        return "\n".join(report)
    
    def _generate_ai_insights(self, scan_results: Dict, analyses: Dict[str, Any]) -> List[str]:
        """Generate AI-powered insights."""
        insights = []
        
        total_files = scan_results.get('total_files', 0)
        if total_files == 0:
            return ["No files analyzed."]
        
        # Content distribution
        categories = {}
        for analysis in analyses.values():
            category = analysis['file_type']['category']
            categories[category] = categories.get(category, 0) + 1
        
        if categories:
            dominant_category = max(categories, key=categories.get)
            insights.append(f"Your collection is {dominant_category}-heavy ({categories[dominant_category]} files)")
        
        # Quality analysis
        ai_scores = [analysis['ai_score'] for analysis in analyses.values()]
        avg_score = sum(ai_scores) / len(ai_scores) if ai_scores else 0
        
        if avg_score > 0.6:
            insights.append("Overall high-quality content detected")
        elif avg_score < 0.3:
            insights.append("Many low-quality files detected - consider cleanup")
        
        # Duplicate analysis
        duplicate_count = sum(len(group) for group in scan_results.get('duplicates', {}).values())
        if duplicate_count > total_files * 0.1:
            insights.append(f"High duplicate rate detected ({duplicate_count} duplicate files)")
        
        # Storage optimization
        total_size = sum(analysis['metadata']['size'] for analysis in analyses.values())
        total_size_gb = total_size / (1024**3)
        
        if total_size_gb > 10:
            insights.append(f"Large storage footprint ({total_size_gb:.1f} GB) - consider optimization")
        
        return insights
    
    def _analyze_content_distribution(self, analyses: Dict[str, Any]) -> Dict[str, Dict]:
        """Analyze content distribution by category."""
        categories = {}
        
        for analysis in analyses.values():
            category = analysis['file_type']['category']
            if category not in categories:
                categories[category] = {
                    'count': 0,
                    'total_size': 0,
                    'ai_scores': []
                }
            
            categories[category]['count'] += 1
            categories[category]['total_size'] += analysis['metadata']['size']
            categories[category]['ai_scores'].append(analysis['ai_score'])
        
        # Calculate averages
        for category in categories:
            scores = categories[category]['ai_scores']
            categories[category]['avg_ai_score'] = sum(scores) / len(scores) if scores else 0
            categories[category]['total_size_mb'] = categories[category]['total_size'] / (1024 * 1024)
            del categories[category]['ai_scores']
        
        return categories
    
    def _generate_recommendations(self, scan_results: Dict, analyses: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        # Duplicate recommendations
        duplicate_count = sum(len(group) for group in scan_results.get('duplicates', {}).values())
        if duplicate_count > 0:
            recommendations.append(f"Remove {duplicate_count} duplicate files to save space")
        
        # Quality recommendations
        low_quality_count = len([a for a in analyses.values() if a['ai_score'] < 0.3])
        if low_quality_count > 0:
            recommendations.append(f"Review {low_quality_count} low-quality files for deletion")
        
        # Storage recommendations
        total_size = sum(analysis['metadata']['size'] for analysis in analyses.values())
        total_size_gb = total_size / (1024**3)
        
        if total_size_gb > 5:
            recommendations.append("Consider compressing large media files")
        
        # Organization recommendations
        categories = {}
        for analysis in analyses.values():
            category = analysis['file_type']['category']
            categories[category] = categories.get(category, 0) + 1
        
        if len(categories) > 5:
            recommendations.append("Organize files into category-based folders")
        
        return recommendations
    
    def _find_high_value_files(self, analyses: Dict[str, Any]) -> List[Tuple[str, float]]:
        """Find high-value files based on AI score."""
        high_value = [(path, analysis['ai_score']) 
                     for path, analysis in analyses.items() 
                     if analysis['ai_score'] > 0.7]
        return sorted(high_value, key=lambda x: x[1], reverse=True)[:10]
    
    def _find_low_quality_files(self, analyses: Dict[str, Any]) -> List[Tuple[str, str]]:
        """Find low-quality files with reasons."""
        low_quality = []
        
        for path, analysis in analyses.items():
            if analysis['ai_score'] < 0.3:
                reason = "Low AI score"
                
                if analysis['file_type']['category'] == 'image':
                    img_feat = analysis.get('image_features', {})
                    if img_feat.get('is_blurry', False):
                        reason = "Blurry image"
                    elif img_feat.get('is_dark', False):
                        reason = "Dark/underexposed image"
                
                elif analysis['file_type']['category'] == 'text':
                    text_feat = analysis.get('text_features', {})
                    if text_feat.get('word_count', 0) < 10:
                        reason = "Very short text content"
                
                low_quality.append((path, reason))
        
        return low_quality[:10]  # Top 10 worst


def run_phase4_scan(config: Dict) -> Dict[str, Any]:
    """Run Phase 4 scan with AI analysis and media optimization."""
    print("🚀 CleanSlate Phase 4 - AI/Media Optimization")
    print("=" * 80)
    
    # Initialize AI components
    ai_analyzer = AIAnalyzer()
    media_optimizer = MediaOptimizer()
    advanced_reporter = AdvancedReporter(ai_analyzer)
    
    # Run base scan
    print("📊 Running base scan...")
    base_results = run_scan(config)
    
    # Get all scanned files
    all_files = []
    for category_files in base_results.values():
        if isinstance(category_files, list):
            all_files.extend(category_files)
        elif isinstance(category_files, dict):
            for group_files in category_files.values():
                if isinstance(group_files, list):
                    all_files.extend(group_files)
    
    # Remove duplicates and get unique files
    unique_files = list(set(all_files))
    print(f"🔍 AI: Analyzing {len(unique_files)} unique files...")
    
    # AI Analysis
    analyses = {}
    for file_path in unique_files:
        if os.path.exists(file_path):
            analyses[file_path] = ai_analyzer.analyze_file_content(file_path)
    
    # Content-based duplicate detection
    content_duplicates = ai_analyzer.find_content_duplicates(unique_files)
    
    # Generate AI report
    ai_report = advanced_reporter.generate_ai_report(base_results, analyses)
    
    # Save AI report
    ai_report_file = "CleanSlate_AI_Report.txt"
    with open(ai_report_file, 'w', encoding='utf-8') as f:
        f.write(ai_report)
    
    # Enhanced results
    enhanced_results = base_results.copy()
    enhanced_results['ai_analyses'] = analyses
    enhanced_results['content_duplicates'] = content_duplicates
    enhanced_results['ai_report'] = ai_report
    
    print("✅ Phase 4 scan complete!")
    print(f"📄 AI Report saved to: {ai_report_file}")
    
    return enhanced_results


def main():
    """Main execution function for Phase 4."""
    print("🧹 CleanSlate Phase 4 - AI/Media Optimization")
    print("=" * 80)
    
    # Load configuration
    config = load_config()
    
    print(f"Configuration loaded from 'config.json'")
    print(f"Directories to scan: {len(config['directories_to_scan'])}")
    print(f"Large file threshold: {config['large_file_threshold_mb']} MB")
    print(f"Old file threshold: {config['old_file_threshold_days']} days")
    print("=" * 80)
    
    # Run Phase 4 scan
    results = run_phase4_scan(config)
    
    # Display summary
    print("\n" + "=" * 80)
    print("📊 PHASE 4 RESULTS SUMMARY")
    print("=" * 80)
    print(f"Total files scanned: {results['total_files']}")
    print(f"AI analyses completed: {len(results.get('ai_analyses', {}))}")
    print(f"Content duplicate groups: {len(results.get('content_duplicates', {}))}")
    print(f"Traditional duplicate groups: {len(results.get('duplicates', {}))}")
    print(f"Large files found: {len(results.get('large_files', []))}")
    print(f"Old files found: {len(results.get('old_files', []))}")
    print(f"Empty files found: {len(results.get('empty_files', []))}")
    print(f"Near-duplicate image groups: {len(results.get('near_duplicates', {}))}")
    print(f"Blurry images found: {len(results.get('blurry_files', []))}")
    
    print("\n✅ Phase 4 complete! AI analysis and recommendations generated.")
    print("💡 Check 'CleanSlate_AI_Report.txt' for detailed insights and recommendations.")


if __name__ == "__main__":
    main() 