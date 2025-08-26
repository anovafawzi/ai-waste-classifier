# Waste Classification AI on Raspberry Pi (Overkill AI Series #1)

```
    _    ___  __        __        _          ____ _               _  __ _           
   / \  |_ _| \ \      / /_ _ ___| |_ ___   / ___| | __ _ ___ ___(_)/ _(_) ___ _ __ 
  / _ \  | |   \ \ /\ / / _` / __| __/ _ \ | |   | |/ _` / __/ __| | |_| |/ _ \ '__|
 / ___ \ | |    \ V  V / (_| \__ \ ||  __/ | |___| | (_| \__ \__ \ |  _| |  __/ |   
/_/   \_\___|    \_/\_/ \__,_|___/\__\___|  \____|_|\__,_|___/___/_|_| |_|\___|_|   
```

This repository documents the evolution of a personal project focused on building an AI-powered waste classification system using a **Raspberry Pi**. The goal is to capture an image of a waste item with a connected camera, send it to a trained AI model, and receive a classification of the item as **rubbish, organics, recyclable, or ecodrop**.

This is a work-in-progress, and I'll be adding more information as the project evolves. I enjoy tinkering with technology, and this project is a way for me to explore the intersection of hardware, machine learning, and something that is useful for the environment.

-----

## Project Phases

This project is broken down into several phases, each with its own folder and a detailed `README.md` file. You can follow the development process by exploring these individual phases.

### 1\. Phase 1: Base Pi Work

The initial phase, located in the `phase1_base_pi_work` folder, covers the foundational setup. This phase serves as the fundamental starting point for the entire project. This stage focuses on the core tasks of getting the Raspberry Pi, its camera, and any other essential peripherals to work together seamlessly.

  * **[Link to Phase 1 README](/phase1_base_pi_work/README.md)**

### 2\. Phase 2: Connecting with Local Vision LLM (+ Prompt Engineering) (in progress)

The next phase, located in the `phase2_connect_llm` folder, this phase represents the first major leap from a simple image capture system to an intelligent classifier by leveraging artificial intelligence for classification. The core idea is to send the captured image to a local Vision LLM (Large Language Model), which is an AI model capable of understanding and processing both text and images.

The primary challenge in this phase is not just connecting to the model but also effectively communicating with it. This is where Prompt Engineering becomes critical. Instead of just sending the image, you craft a specific and detailed prompt to guide the AI's response. For example, a basic prompt might be "What is in this picture?", while a more engineered prompt would be "Analyze the object in this image. Is it 'rubbish', 'organics', 'recyclable', or 'ecodrop'? Respond with only one of those four categories." This process of refining the prompt helps to get a more accurate and structured output from the model, even with a basic setup.

This phase is about exploring the capabilities and limitations of a generic, pre-trained Vision LLM for a specific classification task and learning how to influence its output through careful instruction.

  * **[Link to Phase 2 README](/phase2_connect_llm/README.md)**

### 3\. Phase 3: Optimizing the result by using RAG (Retrieval Augmented Generation) in local vector database (next)

The next phase, located in the `phase3_rag_evolution` folder, covers getting more accurate data by utilizing RAG by having a local knowledge base that stored inside vector database. Building on the foundation of Phase 2, this phase aims to address the potential inaccuracies and hallucinations of a generic Vision LLM. While a vision LLM can "see" and "describe" an image, it may lack the specific, nuanced knowledge required for precise waste classification. For example, it might not know the local recycling rules or the difference between two similar-looking items. So I'll be retrieving the knowledge from the local [city waste management website](https://ccc.govt.nz/services/rubbish-and-recycling/lookupitem).

This is where Retrieval Augmented Generation (RAG) comes into play. The RAG system works by giving the AI access to a private, curated knowledge base. In this project, this knowledge base would contain specific information about waste items, their categories, and perhaps local rules. This information is stored and indexed efficiently in a local Vector Database. When a new image is captured, the system first retrieves the most relevant information from this database (the "Retrieval" part) and then sends both the image and this retrieved information to the Vision LLM.

This process essentially "augments" the AI's general knowledge with specific, accurate data, leading to a much more reliable and context-aware classification. This phase is crucial for moving from a "best guess" system to a more dependable and accurate classifier.

  * **[Link to Phase 3 README](/phase3_rag_evolution/README.md)**

## License

This project is licensed under the **MIT License**.

Copyright (c) [2025] [Anova Fawzi]

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.