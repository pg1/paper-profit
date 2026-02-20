# Neumann Module

## Overview

The **Neumann** module is the educational component of the PaperProfit trading platform, designed to teach users about investing and trading through a structured 21-day learning journey. Named after John von Neumann (a pioneer in computer science and mathematics), this module provides interactive learning materials, quizzes, and exercises to help users build foundational knowledge in financial markets.

## Key Features

- **21-Day Learning Curriculum**: Structured daily lessons covering essential investing concepts
- **Interactive Content**: Study materials, quizzes, and practical exercises for each day
- **Progressive Learning**: Topics range from basic investing concepts to advanced trading strategies
- **Practical Application**: Exercises that apply theoretical knowledge to real-world scenarios

## Content Structure

Each learning day includes:
1. **Study Materials** (`study.txt`) - Core educational content
2. **Quizzes** (`quiz.json`) - Interactive assessments to test understanding
3. **Exercises** (`exercise.html`) - Practical application exercises
4. **Visual Aids** (`1.png`) - Supporting images and diagrams

## Topics Covered

The curriculum progresses through:
- **Days 1-5**: Investing fundamentals (stocks, bonds, ETFs, market mechanics)
- **Days 6-10**: Market analysis (technical indicators, chart reading, fundamental analysis)
- **Days 11-15**: Trading psychology and risk management
- **Days 16-20**: Advanced topics (options, diversification, economic indicators, portfolio building)
- **Day 21**: Final assessment and strategy development

## API Integration

The module is integrated with the main API through dedicated endpoints:
- `/api/learning-days` - Get the complete learning day list
- `/api/learning-days/{day}/study` - Get study content for a specific day
- `/api/learning-days/{day}/quiz` - Get quiz questions and answers
- `/api/learning-days/{day}/exercise` - Get exercise HTML content
- `/api/learning-days/{day}/image` - Get supporting images

## Purpose

Neumann serves as the educational backbone of PaperProfit, ensuring users have the necessary knowledge to make informed trading decisions while using the platform's other features. It transforms beginners into knowledgeable investors through a systematic, hands-on learning approach.